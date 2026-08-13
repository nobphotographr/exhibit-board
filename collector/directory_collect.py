from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from urllib.parse import urljoin, urlparse, urlunparse

import requests
from bs4 import BeautifulSoup

try:
    from .photo_culture_collect import already_published, clean, load_published
    from .website_collect import USER_AGENT, active_candidates, build_candidate, dates_from_text
    from .x_recent_search import load_env, post_candidate
except ImportError:  # Direct script execution
    from photo_culture_collect import already_published, clean, load_published
    from website_collect import USER_AGENT, active_candidates, build_candidate, dates_from_text
    from x_recent_search import load_env, post_candidate


JPS_INDEX = "https://www.jps.gr.jp/members_exhibition/"
PHOTO_ASAHI_INDEX = "https://www.photo-asahi.com/event/exhibition/"
NATIONAL_PHOTO_URL = "https://www.nationalphoto.co.jp/写真展情報/"
CAPA_URLS = [
    f"https://getnavi.jp/capa/exhibition/{region}/"
    for region in (
        "hokkaido", "tohoku", "kanto", "tokyo", "hokuriku",
        "tokai", "kinki", "chugoku", "kyushu",
    )
]

PREFECTURES = (
    "北海道", "青森県", "岩手県", "宮城県", "秋田県", "山形県", "福島県",
    "茨城県", "栃木県", "群馬県", "埼玉県", "千葉県", "東京都", "神奈川県",
    "新潟県", "富山県", "石川県", "福井県", "山梨県", "長野県", "岐阜県",
    "静岡県", "愛知県", "三重県", "滋賀県", "京都府", "大阪府", "兵庫県",
    "奈良県", "和歌山県", "鳥取県", "島根県", "岡山県", "広島県", "山口県",
    "徳島県", "香川県", "愛媛県", "高知県", "福岡県", "佐賀県", "長崎県",
    "熊本県", "大分県", "宮崎県", "鹿児島県", "沖縄県",
)

AREA_PREFIXES = {
    "東京": "東京都", "神奈川": "神奈川県", "京都": "京都府", "大阪": "大阪府",
    "北海道": "北海道", "青森": "青森県", "岩手": "岩手県", "宮城": "宮城県",
    "秋田": "秋田県", "山形": "山形県", "福島": "福島県", "茨城": "茨城県",
    "栃木": "栃木県", "群馬": "群馬県", "埼玉": "埼玉県", "千葉": "千葉県",
    "新潟": "新潟県", "富山": "富山県", "石川": "石川県", "福井": "福井県",
    "山梨": "山梨県", "長野": "長野県", "岐阜": "岐阜県", "静岡": "静岡県",
    "愛知": "愛知県", "三重": "三重県", "滋賀": "滋賀県", "兵庫": "兵庫県",
    "奈良": "奈良県", "和歌山": "和歌山県", "鳥取": "鳥取県", "島根": "島根県",
    "岡山": "岡山県", "広島": "広島県", "山口": "山口県", "徳島": "徳島県",
    "香川": "香川県", "愛媛": "愛媛県", "高知": "高知県", "福岡": "福岡県",
    "佐賀": "佐賀県", "長崎": "長崎県", "熊本": "熊本県", "大分": "大分県",
    "宮崎": "宮崎県", "鹿児島": "鹿児島県", "沖縄": "沖縄県",
}

CITY_HINTS = {
    "札幌市": "北海道", "仙台市": "宮城県", "さいたま市": "埼玉県",
    "横浜市": "神奈川県", "川崎市": "神奈川県", "相模原市": "神奈川県",
    "新潟市": "新潟県", "金沢市": "石川県", "甲府市": "山梨県",
    "長野市": "長野県", "松本市": "長野県", "静岡市": "静岡県",
    "浜松市": "静岡県", "名古屋市": "愛知県", "大津市": "滋賀県",
    "京都市": "京都府", "大阪市": "大阪府", "堺市": "大阪府",
    "神戸市": "兵庫県", "奈良市": "奈良県", "和歌山市": "和歌山県",
    "岡山市": "岡山県", "広島市": "広島県", "高松市": "香川県",
    "松山市": "愛媛県", "福岡市": "福岡県", "北九州市": "福岡県",
    "熊本市": "熊本県", "鹿児島市": "鹿児島県", "那覇市": "沖縄県",
}

TOKYO_WARDS = (
    "千代田区", "中央区", "港区", "新宿区", "文京区", "台東区", "墨田区",
    "江東区", "品川区", "目黒区", "大田区", "世田谷区", "渋谷区", "中野区",
    "杉並区", "豊島区", "北区", "荒川区", "板橋区", "練馬区", "足立区",
    "葛飾区", "江戸川区",
)


@dataclass(frozen=True)
class PhotoAsahiListing:
    url: str
    prefecture: str | None


def source_event_url(base_url: str, title: str, start_date: str, end_date: str) -> str:
    digest = hashlib.sha256(f"{title}|{start_date}|{end_date}".encode("utf-8")).hexdigest()[:12]
    parsed = urlparse(base_url)
    return urlunparse(parsed._replace(fragment=f"exhibit-board-{digest}"))


def location_key(value: str) -> str:
    normalized = clean(value).lower()
    normalized = normalized.replace("キャノン", "キヤノン").replace("フジフィルム", "フジフイルム")
    return re.sub(r"[^0-9a-zぁ-んァ-ヶ一-龠α]", "", normalized)


def prefecture_from_text(value: str | None) -> str | None:
    text = clean(value or "")
    direct = next((prefecture for prefecture in PREFECTURES if prefecture in text), None)
    if direct:
        return direct
    if any(ward in text for ward in TOKYO_WARDS):
        return "東京都"
    for city, prefecture in CITY_HINTS.items():
        if city in text:
            return prefecture
    for prefix, prefecture in AREA_PREFIXES.items():
        if text.startswith(f"{prefix}・") or text == prefix:
            return prefecture
    return None


class LocationResolver:
    def __init__(self, published: list[dict], registry_path: Path | None = None):
        self.locations: list[tuple[str, str, str | None]] = []
        for event in published:
            venue = str(event.get("venue") or "")
            prefecture = str(event.get("prefecture") or "")
            if venue and prefecture in PREFECTURES:
                self.locations.append((location_key(venue), prefecture, event.get("address")))
        if registry_path and registry_path.exists():
            payload = json.loads(registry_path.read_text(encoding="utf-8"))
            for record in payload.get("venues", []):
                prefecture = prefecture_from_text(record.get("area")) or prefecture_from_text(record.get("address"))
                if record.get("name") and prefecture:
                    self.locations.append((
                        location_key(record["name"]), prefecture, record.get("address"),
                    ))

    def resolve(self, venue: str, address: str | None = None) -> tuple[str | None, str | None]:
        direct = prefecture_from_text(address) or prefecture_from_text(venue)
        if direct:
            return direct, address
        key = location_key(venue)
        exact = next((item for item in self.locations if item[0] == key), None)
        if exact:
            return exact[1], address or exact[2]
        if len(key) >= 5:
            partial = next(
                (item for item in self.locations if len(item[0]) >= 5 and (key in item[0] or item[0] in key)),
                None,
            )
            if partial:
                return partial[1], address or partial[2]
        return None, address


def parse_jps_index(html: str) -> list[str]:
    soup = BeautifulSoup(html, "html.parser")
    urls = []
    for link in soup.select(".eventBlock .summary a[href]"):
        label = clean(link.get_text(" ", strip=True))
        url = urljoin(JPS_INDEX, link.get("href", ""))
        if "展覧会情報" in label and url not in urls:
            urls.append(url)
    return urls


def parse_jps_detail(html: str, page_url: str, resolver: LocationResolver) -> list[dict]:
    soup = BeautifulSoup(html, "html.parser")
    results = []
    for row in soup.select(".entry-content table tr"):
        cells = [clean(cell.get_text(" ", strip=True)) for cell in row.select("td")]
        if len(cells) < 4 or "開催日" in cells[2]:
            continue
        member, exhibition, date_text, venue = cells[:4]
        dates = dates_from_text(date_text)
        if not exhibition or not venue or not dates:
            continue
        prefecture, address = resolver.resolve(venue)
        if not prefecture:
            continue
        title = clean(f"{member} {exhibition}")
        results.append(build_candidate(
            title=title, venue=venue, prefecture=prefecture, address=address,
            start_date=dates[0], end_date=dates[1],
            source_url=source_event_url(page_url, title, dates[0], dates[1]),
            source_name="日本写真家協会 会員展覧会情報",
            card_text=" | ".join(cells),
            notes="日本写真家協会の会員提供情報から確認",
        ))
    return results


def parse_photo_asahi_listing(html: str, base_url: str = PHOTO_ASAHI_INDEX) -> list[PhotoAsahiListing]:
    soup = BeautifulSoup(html, "html.parser")
    results = []
    for card in soup.select(".box_news"):
        link = card.select_one("h3 a[href]")
        if not link:
            continue
        prefecture_node = card.select_one(".btn-primary")
        results.append(PhotoAsahiListing(
            url=urljoin(base_url, link.get("href", "")),
            prefecture=prefecture_from_text(prefecture_node.get_text(" ", strip=True)) if prefecture_node else None,
        ))
    return results


def parse_photo_asahi_detail(html: str, page_url: str, fallback_prefecture: str | None = None) -> list[dict]:
    soup = BeautifulSoup(html, "html.parser")
    title_node = soup.select_one("#leaf h2.t_main")
    body = soup.select_one("#leaf_inner")
    date_node = body.select_one(":scope > p") if body else None
    address_node = soup.select_one("#leaf_inner > #disp_address, #leaf_inner p#disp_address")
    if not title_node or not body or not date_node:
        return []
    title = clean(title_node.get_text(" ", strip=True))
    structured_dates = []
    for event_date in soup.select(".event_date"):
        values = [clean(value) for value in event_date.stripped_strings if clean(value)]
        year = next((value for value in values if re.fullmatch(r"20\d{2}", value)), None)
        month_day = next((value for value in values if re.fullmatch(r"\d{1,2}/\d{1,2}", value)), None)
        if year and month_day:
            month, day = map(int, month_day.split("/"))
            structured_dates.append(f"{int(year):04d}-{month:02d}-{day:02d}")
    dates = (
        (structured_dates[0], structured_dates[-1])
        if len(structured_dates) >= 2 else dates_from_text(date_node.get_text(" ", strip=True))
    )
    body_text = body.get_text("\n", strip=True)
    venue_match = re.search(r"【会場】\s*([^\n]+)", body_text)
    if not dates or not venue_match:
        return []
    venue = clean(venue_match.group(1))
    address = clean(address_node.get_text(" ", strip=True)) if address_node else None
    prefecture = prefecture_from_text(address) or fallback_prefecture
    if not prefecture:
        prefecture_node = soup.select_one("dl.list_local dt.btn-primary")
        prefecture = prefecture_from_text(prefecture_node.get_text(" ", strip=True)) if prefecture_node else None
    if not prefecture:
        return []
    return [build_candidate(
        title=title, venue=venue, prefecture=prefecture, address=address,
        start_date=dates[0], end_date=dates[1], source_url=page_url,
        source_name="全日本写真連盟 写真展情報", card_text=body_text,
        notes="全日本写真連盟の写真展情報から確認",
    )]


def parse_national_photo(html: str, page_url: str = NATIONAL_PHOTO_URL) -> list[dict]:
    soup = BeautifulSoup(html, "html.parser")
    results = []
    for figure in soup.select("figure.wp-block-table"):
        rows = figure.select("table tr")
        if len(rows) < 2:
            continue
        info = clean(rows[0].get_text(" ", strip=True))
        venue_node = figure.select_one("figcaption")
        official = rows[0].select_one("a[href]")
        venue = clean(venue_node.get_text(" ", strip=True)) if venue_node else ""
        address_match = re.search(r"住所[：:]\s*(.+?)(?=\s*(?:電話|TEL|時間)[：:]|$)", info)
        address = clean(address_match.group(1)) if address_match else None
        prefecture = prefecture_from_text(address)
        if not venue or not official or not prefecture:
            continue
        official_url = urljoin(page_url, official.get("href", ""))
        for row in rows[1:]:
            lines = [clean(value) for value in row.stripped_strings if clean(value)]
            date_index = next((index for index, value in enumerate(lines) if re.search(r"20\d{2}", value)), None)
            if date_index is None:
                continue
            dates = dates_from_text(lines[date_index])
            title = clean(" ".join(lines[:date_index]))
            if not dates or not title:
                continue
            results.append(build_candidate(
                title=title, venue=venue, prefecture=prefecture, address=address,
                start_date=dates[0], end_date=dates[1],
                source_url=source_event_url(official_url, title, dates[0], dates[1]),
                source_name=f"{venue} 公式サイト（ナショナル・フォートで会期確認）",
                card_text=" | ".join(lines),
            ))
    return results


def parse_capa(html: str, page_url: str) -> list[dict]:
    soup = BeautifulSoup(html, "html.parser")
    results = []
    for section in soup.select(".entry-content > section"):
        place = section.select_one(":scope > .place")
        venue_node = place.select_one("h4") if place else None
        if not place or not venue_node:
            continue
        official = next(
            (link for link in place.select("a[href]") if "maps." not in link.get("href", "")),
            None,
        )
        heading = section.find_previous("h2")
        prefecture = prefecture_from_text(heading.get_text(" ", strip=True)) if heading else None
        venue = clean(venue_node.get_text(" ", strip=True))
        if not official or not prefecture or not venue:
            continue
        official_url = urljoin(page_url, official.get("href", ""))
        for item in section.select(":scope > ul > li"):
            date_node = item.select_one(".date")
            title_node = item.select_one("p")
            if not date_node or not title_node:
                continue
            dates = dates_from_text(date_node.get_text(" ", strip=True))
            notes_node = title_node.select_one("small")
            notes = clean(notes_node.get_text(" ", strip=True)) if notes_node else None
            title_soup = BeautifulSoup(str(title_node), "html.parser")
            for small in title_soup.select("small"):
                small.decompose()
            title = clean(title_soup.get_text(" ", strip=True))
            if not dates or not title:
                continue
            results.append(build_candidate(
                title=title, venue=venue, prefecture=prefecture,
                start_date=dates[0], end_date=dates[1],
                source_url=source_event_url(official_url, title, dates[0], dates[1]),
                source_name=f"{venue} 公式サイト（CAPA CAMERA WEBで会期確認）",
                card_text=clean(item.get_text(" ", strip=True)), notes=notes,
            ))
    return results


class DirectoryCollector:
    def __init__(self, published: list[dict], session: requests.Session | None = None):
        self.session = session or requests.Session()
        self.session.headers.update({"User-Agent": USER_AGENT})
        registry = Path(__file__).with_name("photo_culture_venues.json")
        self.resolver = LocationResolver(published, registry)
        self.failures = 0

    def get(self, url: str) -> str | None:
        try:
            response = self.session.get(url, timeout=30)
            response.raise_for_status()
            response.encoding = response.apparent_encoding or "utf-8"
            return response.text
        except requests.RequestException as exc:
            self.failures += 1
            print(f"warning: {url}: {exc}", file=sys.stderr)
            return None

    def collect_jps(self, months: int = 3) -> list[dict]:
        index = self.get(JPS_INDEX)
        if not index:
            return []
        results = []
        for url in parse_jps_index(index)[:months]:
            html = self.get(url)
            if html:
                results.extend(parse_jps_detail(html, url, self.resolver))
        return results

    def collect_photo_asahi(self, pages: int = 2) -> list[dict]:
        listings: dict[str, PhotoAsahiListing] = {}
        for page in range(1, pages + 1):
            url = PHOTO_ASAHI_INDEX if page == 1 else urljoin(PHOTO_ASAHI_INDEX, f"{page}.htm")
            html = self.get(url)
            if not html:
                continue
            for listing in parse_photo_asahi_listing(html, url):
                listings[listing.url] = listing
        results = []
        for listing in listings.values():
            html = self.get(listing.url)
            if html:
                results.extend(parse_photo_asahi_detail(html, listing.url, listing.prefecture))
        return results

    def collect_national_photo(self) -> list[dict]:
        html = self.get(NATIONAL_PHOTO_URL)
        return parse_national_photo(html) if html else []

    def collect_capa(self) -> list[dict]:
        results = []
        for url in CAPA_URLS:
            html = self.get(url)
            if html:
                results.extend(parse_capa(html, url))
        return results

    def collect(self) -> list[dict]:
        candidates = [
            *self.collect_jps(),
            *self.collect_photo_asahi(),
            *self.collect_national_photo(),
            *self.collect_capa(),
        ]
        unique = {candidate["event_fingerprint"]: candidate for candidate in candidates}
        return active_candidates(list(unique.values()))


def main() -> int:
    parser = argparse.ArgumentParser(description="Collect photography association and media directories")
    parser.add_argument("--env-file", type=Path, default=Path(".env"))
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    load_env(args.env_file)
    endpoint = os.environ.get("COLLECTOR_ENDPOINT", "https://exhibit.iruagaru.com").rstrip("/")
    api_key = os.environ.get("COLLECTOR_API_KEY", "")
    if not args.dry_run and not api_key:
        raise SystemExit("COLLECTOR_API_KEY is required unless --dry-run is used")

    published = load_published(endpoint)
    collector = DirectoryCollector(published)
    candidates = collector.collect()
    # Treat candidates accepted earlier in this same run as published too. This
    # catches one exhibition listed with slightly different wording by two
    # directories before the public API cache has had a chance to refresh.
    seen_events = list(published)
    added = 0
    duplicates = 0
    for candidate in candidates:
        if already_published(candidate, seen_events):
            duplicates += 1
            continue
        if not args.dry_run:
            post_candidate(f"{endpoint}/api/internal/candidates", api_key, candidate)
        print(json.dumps({
            "title": candidate["extracted"]["title"],
            "venue": candidate["extracted"]["venue"],
            "prefecture": candidate["extracted"]["prefecture"],
            "start_date": candidate["extracted"]["start_date"],
            "end_date": candidate["extracted"]["end_date"],
            "source_url": candidate["source"]["url"],
        }, ensure_ascii=False))
        seen_events.append(candidate["extracted"])
        added += 1
    print(
        f"total={len(candidates)} new={added} duplicates={duplicates} failures={collector.failures}",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

from __future__ import annotations

import argparse
import hashlib
import json
import os
from dataclasses import dataclass
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Callable
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

try:
    from .extract import extract_dates, fingerprint, normalize
    from .x_recent_search import load_env, post_candidate
except ImportError:  # Direct script execution
    from extract import extract_dates, fingerprint, normalize
    from x_recent_search import load_env, post_candidate


USER_AGENT = "ExhibitBoardBot/0.1 (+https://exhibit.iruagaru.com)"


@dataclass(frozen=True)
class SiteDefinition:
    url: str
    name: str
    parser: Callable[[str], list[dict]]
    encoding: str | None = None


def text_hash(text: str) -> str:
    return hashlib.sha256(normalize(text).encode("utf-8")).hexdigest()


def build_candidate(
    *, title: str, venue: str, prefecture: str, start_date: str, end_date: str,
    source_url: str, source_name: str, card_text: str, address: str | None = None,
) -> dict:
    extracted = {
        "title": title.strip(),
        "host_name": None,
        "venue": venue.strip(),
        "address": address,
        "prefecture": prefecture,
        "price": None,
        "start_date": start_date,
        "end_date": end_date,
        "notes": None,
    }
    return {
        "event_fingerprint": fingerprint(extracted, source_url),
        "confidence": 1.0,
        "extracted": extracted,
        "source": {
            "type": "website",
            "key": source_url,
            "url": source_url,
            "name": source_name,
            "author_handle": None,
            "content_hash": text_hash(card_text),
        },
    }


def dates_from_text(value: str) -> tuple[str, str] | None:
    start, end = extract_dates(normalize(value), datetime.now(timezone.utc))
    if start and end:
        return start, end
    return None


def parse_fujifilm(html: str) -> list[dict]:
    soup = BeautifulSoup(html, "html.parser")
    results = []
    for card in soup.select("a.area-link[href*='/exhibition/']"):
        title_node = card.select_one(".area-link__title")
        data = card.select("p.data-text")
        if not title_node or len(data) < 2:
            continue
        dates = dates_from_text(data[0].get_text(" ", strip=True))
        if not dates:
            continue
        url = urljoin("https://fujifilmsquare.jp/event.html", card.get("href", ""))
        results.append(build_candidate(
            title=title_node.get_text(" ", strip=True),
            venue=f"フジフイルム スクエア {data[1].get_text(' ', strip=True)}",
            prefecture="東京都",
            address="東京都港区赤坂9-7-3 東京ミッドタウン ミッドタウン・ウェスト1F",
            start_date=dates[0],
            end_date=dates[1],
            source_url=url,
            source_name="フジフイルム スクエア",
            card_text=card.get_text(" ", strip=True),
        ))
    return unique_sources(results)


def parse_canon(html: str) -> list[dict]:
    soup = BeautifulSoup(html, "html.parser")
    location_map = {
        "品川": ("キヤノンギャラリー S（品川）", "東京都"),
        "銀座": ("キヤノンギャラリー銀座", "東京都"),
        "大阪": ("キヤノンギャラリー大阪", "大阪府"),
    }
    results = []
    for card in soup.select("a.pnl[href*='/event/photographyexhibition/gallery/']"):
        title_node = card.select_one(".title")
        date_node = card.select_one(".description dd")
        if not title_node or not date_node:
            continue
        dates = dates_from_text(date_node.get_text(" ", strip=True))
        if not dates:
            continue
        description_spans = [node.get_text(" ", strip=True) for node in card.select(".description > span")]
        location = next((value for value in description_spans if value in location_map), None)
        if not location:
            continue
        venue, prefecture = location_map[location]
        url = urljoin("https://personal.canon.jp/showroom/gallery", card.get("href", ""))
        results.append(build_candidate(
            title=title_node.get_text(" ", strip=True),
            venue=venue,
            prefecture=prefecture,
            start_date=dates[0],
            end_date=dates[1],
            source_url=url,
            source_name="キヤノンギャラリー",
            card_text=card.get_text(" ", strip=True),
        ))
    return unique_sources(results)


def parse_sony(html: str) -> list[dict]:
    soup = BeautifulSoup(html, "html.parser")
    results = []
    for card in soup.select("#schedule li a[href*='/camera/imaging-gallery/detail/']"):
        date_node = card.select_one(".data")
        if not date_node:
            continue
        dates = dates_from_text(date_node.get_text(" ", strip=True))
        if not dates:
            continue
        title = card.get("aria-label") or card.select_one("figcaption").get_text(" ", strip=True)
        url = urljoin("https://www.sony.jp/camera/imaging-gallery/", card.get("href", ""))
        results.append(build_candidate(
            title=title,
            venue="Sony Imaging Gallery 銀座",
            prefecture="東京都",
            address="東京都中央区銀座5-8-1 銀座プレイス6階",
            start_date=dates[0],
            end_date=dates[1],
            source_url=url,
            source_name="Sony Imaging Gallery",
            card_text=card.get_text(" ", strip=True),
        ))
    return unique_sources(results)


def parse_jcii(html: str) -> list[dict]:
    soup = BeautifulSoup(html, "html.parser")
    results = []
    for card in soup.select("section.open-exhibition .item, section.prepared-exhibition .item"):
        link = card.select_one("h3.entry-title a")
        description = card.select_one(".exhibision-description")
        if not link or not description:
            continue
        dates = dates_from_text(description.get_text(" ", strip=True))
        if not dates:
            continue
        url = urljoin("https://www.jcii-cameramuseum.jp/photosalon/photo-exhibition/", link.get("href", ""))
        results.append(build_candidate(
            title=link.get_text(" ", strip=True),
            venue="JCIIフォトサロン",
            prefecture="東京都",
            address="東京都千代田区一番町25番地 JCII一番町ビル",
            start_date=dates[0],
            end_date=dates[1],
            source_url=url,
            source_name="JCIIフォトサロン",
            card_text=card.get_text(" ", strip=True),
        ))
    return unique_sources(results)


def unique_sources(candidates: list[dict]) -> list[dict]:
    return list({candidate["source"]["key"]: candidate for candidate in candidates}.values())


def active_candidates(candidates: list[dict]) -> list[dict]:
    today = date.today().isoformat()
    return [candidate for candidate in candidates if candidate["extracted"]["end_date"] >= today]


SITES = {
    "fujifilm": SiteDefinition("https://fujifilmsquare.jp/event.html", "フジフイルム スクエア", parse_fujifilm),
    "canon": SiteDefinition("https://personal.canon.jp/showroom/gallery", "キヤノンギャラリー", parse_canon),
    "sony": SiteDefinition("https://www.sony.jp/camera/imaging-gallery/", "Sony Imaging Gallery", parse_sony, "cp932"),
    "jcii": SiteDefinition("https://www.jcii-cameramuseum.jp/photosalon/photo-exhibition/", "JCIIフォトサロン", parse_jcii),
}


def fetch_site(definition: SiteDefinition) -> str:
    response = requests.get(definition.url, headers={"User-Agent": USER_AGENT}, timeout=30)
    response.raise_for_status()
    if definition.encoding:
        return response.content.decode(definition.encoding, errors="replace")
    response.encoding = response.apparent_encoding or "utf-8"
    return response.text


def main() -> int:
    parser = argparse.ArgumentParser(description="Collect exhibition schedules from official venue sites")
    parser.add_argument("--env-file", type=Path, default=Path(".env"))
    parser.add_argument("--site", choices=["all", *SITES], default="all")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    load_env(args.env_file)
    endpoint = os.environ.get("COLLECTOR_ENDPOINT", "").rstrip("/")
    api_key = os.environ.get("COLLECTOR_API_KEY", "")
    if not args.dry_run and (not endpoint or not api_key):
        raise SystemExit("COLLECTOR_ENDPOINT and COLLECTOR_API_KEY are required unless --dry-run is used")

    selected = SITES.items() if args.site == "all" else [(args.site, SITES[args.site])]
    total = 0
    for key, definition in selected:
        candidates = active_candidates(definition.parser(fetch_site(definition)))
        for candidate in candidates:
            if not args.dry_run:
                post_candidate(f"{endpoint}/api/internal/candidates", api_key, candidate)
            print(json.dumps({
                "site": key,
                "title": candidate["extracted"]["title"],
                "start_date": candidate["extracted"]["start_date"],
                "end_date": candidate["extracted"]["end_date"],
                "source_url": candidate["source"]["url"],
            }, ensure_ascii=False))
            total += 1
        print(f"{key}: {len(candidates)} candidates")
    print(f"total={total}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

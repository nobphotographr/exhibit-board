from __future__ import annotations

import argparse
import json
import os
import re
import sys
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup

try:
    from .extract import normalize
    from .website_collect import USER_AGENT, active_candidates, build_candidate, dates_from_text
    from .x_recent_search import load_env, post_candidate
except ImportError:  # Direct script execution
    from extract import normalize
    from website_collect import USER_AGENT, active_candidates, build_candidate, dates_from_text
    from x_recent_search import load_env, post_candidate


BASE_URL = "https://photoandculture-tokyo.com/"
LIST_URL = urljoin(BASE_URL, "exhibision_list.php")
SOCIAL_HOSTS = {
    "facebook.com", "instagram.com", "threads.net", "twitter.com", "x.com",
    "youtube.com", "youtu.be", "line.me", "social-plugins.line.me",
}


@dataclass(frozen=True)
class Listing:
    article_url: str
    prefecture: str
    venue: str
    date_text: str
    headline: str


def clean(value: str) -> str:
    return re.sub(r"\s+", " ", normalize(value)).strip()


def parse_listing_page(html: str) -> list[Listing]:
    soup = BeautifulSoup(html, "html.parser")
    results = []
    for card in soup.select("#contents_set > figure"):
        article = card.select_one("a[href*='contents.php?i=']")
        category = card.select_one("a.cate")
        headline = card.select_one("strong.ah, strong")
        spans = [clean(node.get_text(" ", strip=True)) for node in card.select("span")]
        venue_text = next((value for value in spans if value.startswith("会場")), "")
        date_text = next((value for value in spans if value.startswith("会期")), "")
        if not article or not category or not headline or not venue_text or not date_text:
            continue
        venue = re.sub(r"^会場\s*", "", venue_text).strip()
        if not venue:
            continue
        results.append(Listing(
            article_url=urljoin(BASE_URL, article.get("href", "")),
            prefecture=clean(category.get_text(" ", strip=True)),
            venue=venue,
            date_text=date_text,
            headline=clean(headline.get_text(" ", strip=True)),
        ))
    return results


def parse_article(html: str, fallback_headline: str) -> tuple[str, str | None, str | None]:
    soup = BeautifulSoup(html, "html.parser")
    body = soup.select_one("#contents_body")
    if not body:
        return fallback_headline, None, None

    title = None
    for quote in body.select("blockquote"):
        items = [clean(item.get_text(" ", strip=True)) for item in quote.select("li")]
        marker = next((index for index, value in enumerate(items) if "展覧会情報" in value), None)
        if marker is None:
            continue
        title_parts = []
        for value in items[marker + 1:]:
            if value and not re.match(r"^(会期|時間|会場|場所|休|料金|入場|主催|URL)[:：]", value):
                if re.fullmatch(r"[［\[].+?[］\]]", value):
                    continue
                title_parts.append(value)
                if len(title_parts) == 1 and re.search(r"(?:企画展|写真展)$", value):
                    continue
                break
        if title_parts:
            title = " ".join(title_parts)
        if title:
            break

    if not title:
        heading = soup.select_one("#contents_header h1")
        editorial = clean(heading.get_text(" ", strip=True)) if heading else fallback_headline
        title = re.sub(r"^.*?(?:にて|で)[、,]\s*", "", editorial)
        title = re.sub(r"(?:が開催される|が開催)$", "", title).strip()

    gallery_link = soup.select_one("#exhibision_info a.glink[href*='gallerydet.php?i=']")
    gallery_url = urljoin(BASE_URL, gallery_link.get("href", "")) if gallery_link else None

    external_links = []
    related_heading = next(
        (node for node in body.find_all(["p", "h2", "h3", "h4", "strong"])
         if "関連リンク" in clean(node.get_text(" ", strip=True))),
        None,
    )
    related_area = []
    if related_heading:
        for node in related_heading.find_all_next():
            if node.get("id") == "exhibision_info":
                break
            if node.name == "a" and node.get("href"):
                related_area.append(node)
    for link in related_area:
        url = urljoin(BASE_URL, link.get("href", ""))
        host = urlparse(url).hostname or ""
        host = host.removeprefix("www.")
        if (not host or host.endswith("photoandculture-tokyo.com") or host in SOCIAL_HOSTS
                or "/share" in urlparse(url).path or "/lineit/" in urlparse(url).path):
            continue
        external_links.append(url)
    related_url = external_links[0] if external_links else None
    return title, gallery_url, related_url


def parse_gallery_detail(html: str) -> tuple[str | None, str | None]:
    soup = BeautifulSoup(html, "html.parser")
    address = None
    official_url = None
    for row in soup.select("#dleft_blk li"):
        label = row.select_one("p.dt")
        if not label:
            continue
        label_text = clean(label.get_text(" ", strip=True))
        if label_text == "住所":
            value = clean(row.get_text(" ", strip=True))
            address = re.sub(r"^住所\s*(?:〒?\d{3}-?\d{4}\s*)?", "", value).strip() or None
        elif label_text == "URL":
            link = row.select_one("a[href]")
            if link:
                official_url = urljoin(BASE_URL, link.get("href", ""))
    return address, official_url


def compact_key(value: str) -> str:
    normalized = normalize(value).lower()
    normalized = normalized.replace("キャノン", "キヤノン")
    normalized = normalized.replace("フジフィルム", "フジフイルム").replace("富士フィルム", "富士フイルム")
    normalized = re.sub(r"(?:写真展|作品展|個展)", "", normalized)
    return re.sub(r"[^0-9a-zA-Zぁ-んァ-ヶ一-龠]", "", normalized)


def already_published(candidate: dict, published: list[dict]) -> bool:
    extracted = candidate["extracted"]
    venue_key = compact_key(extracted["venue"])
    title_key = compact_key(extracted["title"])
    for event in published:
        if event.get("start_date") != extracted["start_date"] or event.get("end_date") != extracted["end_date"]:
            continue
        existing_venue = compact_key(str(event.get("venue") or ""))
        existing_title = compact_key(str(event.get("title") or ""))
        same_venue = venue_key in existing_venue or existing_venue in venue_key
        same_title = title_key in existing_title or existing_title in title_key
        if same_venue or same_title:
            return True
    return False


class PhotoCultureCollector:
    def __init__(self, session: requests.Session | None = None):
        self.session = session or requests.Session()
        self.session.headers.update({"User-Agent": USER_AGENT})
        self.gallery_cache: dict[str, tuple[str | None, str | None]] = {}

    def get(self, url: str) -> str:
        response = self.session.get(url, timeout=30)
        response.raise_for_status()
        response.encoding = response.apparent_encoding or "utf-8"
        return response.text

    def collect(self, max_pages: int = 20) -> list[dict]:
        listings: dict[tuple[str, str, str], Listing] = {}
        for page in range(max_pages):
            try:
                page_listings = parse_listing_page(self.get(f"{LIST_URL}?c=0&s=&p={page}"))
            except requests.RequestException as exc:
                print(f"warning: listing page {page}: {exc}", file=sys.stderr)
                break
            new_count = 0
            for listing in page_listings:
                key = (listing.article_url, listing.venue, listing.date_text)
                if key not in listings:
                    listings[key] = listing
                    new_count += 1
            if not page_listings or new_count == 0:
                break

        results = []
        for listing in listings.values():
            dates = dates_from_text(listing.date_text)
            if not dates or dates[1] < date.today().isoformat():
                continue
            try:
                article_html = self.get(listing.article_url)
            except requests.RequestException as exc:
                print(f"warning: article {listing.article_url}: {exc}", file=sys.stderr)
                continue
            title, gallery_url, related_url = parse_article(article_html, listing.headline)
            if not gallery_url:
                continue
            if gallery_url not in self.gallery_cache:
                try:
                    self.gallery_cache[gallery_url] = parse_gallery_detail(self.get(gallery_url))
                except requests.RequestException as exc:
                    print(f"warning: gallery {gallery_url}: {exc}", file=sys.stderr)
                    self.gallery_cache[gallery_url] = (None, None)
            address, official_url = self.gallery_cache[gallery_url]
            source_url = related_url or official_url
            if not source_url:
                continue
            host = (urlparse(source_url).hostname or "").removeprefix("www.")
            if host in SOCIAL_HOSTS:
                continue
            results.append(build_candidate(
                title=title,
                venue=listing.venue,
                prefecture=listing.prefecture,
                address=address,
                start_date=dates[0], end_date=dates[1],
                source_url=source_url,
                source_name=f"{listing.venue} 公式告知（Photo & Culture, Tokyoで確認）",
                card_text=clean(BeautifulSoup(article_html, "html.parser").get_text(" ", strip=True)),
            ))
        return active_candidates(results)


def load_published(endpoint: str) -> list[dict]:
    response = requests.get(f"{endpoint}/api/events", headers={"User-Agent": USER_AGENT}, timeout=30)
    response.raise_for_status()
    payload = response.json()
    return payload if isinstance(payload, list) else payload.get("events", [])


def main() -> int:
    parser = argparse.ArgumentParser(description="Discover official exhibition links through Photo & Culture, Tokyo")
    parser.add_argument("--env-file", type=Path, default=Path(".env"))
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--max-pages", type=int, default=20)
    args = parser.parse_args()

    load_env(args.env_file)
    endpoint = os.environ.get("COLLECTOR_ENDPOINT", "https://exhibit.iruagaru.com").rstrip("/")
    api_key = os.environ.get("COLLECTOR_API_KEY", "")
    if not args.dry_run and not api_key:
        raise SystemExit("COLLECTOR_API_KEY is required unless --dry-run is used")

    published = load_published(endpoint)
    candidates = PhotoCultureCollector().collect(max_pages=args.max_pages)
    added = 0
    duplicates = 0
    for candidate in candidates:
        if already_published(candidate, published):
            duplicates += 1
            continue
        if not args.dry_run:
            post_candidate(f"{endpoint}/api/internal/candidates", api_key, candidate)
        print(json.dumps({
            "title": candidate["extracted"]["title"],
            "venue": candidate["extracted"]["venue"],
            "start_date": candidate["extracted"]["start_date"],
            "end_date": candidate["extracted"]["end_date"],
            "source_url": candidate["source"]["url"],
        }, ensure_ascii=False))
        added += 1
    print(f"total={len(candidates)} new={added} duplicates={duplicates}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

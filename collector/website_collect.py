from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
from dataclasses import dataclass
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Callable
from urllib.parse import unquote, urljoin

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
    normalized = normalize(value)
    normalized = re.sub(
        r"(20\d{2})[./](\d{1,2})[./](\d{1,2})",
        lambda match: f"{match.group(1)}年{match.group(2)}月{match.group(3)}日",
        normalized,
    )
    slash_range = re.search(
        r"(?<!\d)(?P<sm>\d{1,2})/(?P<sd>\d{1,2})[^~〜～–—]{0,20}[~〜～–—]\s*"
        r"(?:(?P<em>\d{1,2})/)?(?P<ed>\d{1,2})",
        normalized,
    )
    if slash_range:
        start_month = int(slash_range.group("sm"))
        end_month = int(slash_range.group("em") or start_month)
        year = datetime.now(timezone.utc).year
        end_year = year + 1 if end_month < start_month else year
        return (
            f"{year:04d}-{start_month:02d}-{int(slash_range.group('sd')):02d}",
            f"{end_year:04d}-{end_month:02d}-{int(slash_range.group('ed')):02d}",
        )
    start, end = extract_dates(normalized, datetime.now(timezone.utc))
    if start and end:
        return start, end
    return None


def english_dates_from_text(value: str) -> tuple[str, str] | None:
    months = {
        "Jan": 1, "Feb": 2, "Mar": 3, "Apr": 4, "May": 5, "Jun": 6,
        "Jul": 7, "Aug": 8, "Sep": 9, "Oct": 10, "Nov": 11, "Dec": 12,
    }
    match = re.search(
        r"(?P<sm>[A-Z][a-z]{2})\.?\s*(?P<sd>\d{1,2})\s*[–—-]\s*"
        r"(?P<em>[A-Z][a-z]{2})\.?\s*(?P<ed>\d{1,2}),?\s*(?P<year>20\d{2})",
        normalize(value),
    )
    if not match or match.group("sm") not in months or match.group("em") not in months:
        return None
    end_year = int(match.group("year"))
    start_month = months[match.group("sm")]
    end_month = months[match.group("em")]
    start_year = end_year - 1 if end_month < start_month else end_year
    return (
        f"{start_year:04d}-{start_month:02d}-{int(match.group('sd')):02d}",
        f"{end_year:04d}-{end_month:02d}-{int(match.group('ed')):02d}",
    )


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


def fujifilm_regional_parser(
    *, venue: str, prefecture: str, address: str, base_url: str,
) -> Callable[[str], list[dict]]:
    def parse(html: str) -> list[dict]:
        soup = BeautifulSoup(html, "html.parser")
        results = []
        for card in soup.select("#nowevent_list .nowevent"):
            link = card.select_one(".salonbox h4 a[href]")
            date_node = card.select_one(".salonbox .exdate")
            if not link or not date_node:
                continue
            dates = dates_from_text(date_node.get_text(" ", strip=True))
            if not dates:
                continue
            url = urljoin(base_url, link.get("href", ""))
            results.append(build_candidate(
                title=link.get_text(" ", strip=True),
                venue=venue,
                prefecture=prefecture,
                address=address,
                start_date=dates[0],
                end_date=dates[1],
                source_url=url,
                source_name=venue,
                card_text=card.get_text(" ", strip=True),
            ))
        return unique_sources(results)

    return parse


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


def parse_sony_alpha_plaza(html: str) -> list[dict]:
    match = re.search(r"callback\s*\((.*)\)\s*;?\s*$", html, re.DOTALL)
    if not match:
        return []
    data = json.loads(match.group(1))
    location_map = {
        "札幌": ("αプラザ札幌", "北海道", "北海道札幌市中央区南一条西3-8-20 4階"),
        "銀座": ("αプラザ銀座", "東京都", "東京都中央区銀座5-8-1 銀座プレイス4階"),
        "名古屋": ("αプラザ名古屋", "愛知県", "愛知県名古屋市中区錦3-24-17 BINO栄3階"),
        "大阪": ("αプラザ大阪", "大阪府", "大阪府大阪市北区梅田2-2-22 ハービスエント4階"),
        "福岡天神": ("αプラザ福岡天神", "福岡県", "福岡県福岡市中央区今泉1-19-22 天神CLASS 1階"),
    }
    results = []
    for event in data.get("EventInformationList", []):
        if event.get("RefineClassification__c") != "ギャラリー":
            continue
        place = event.get("Place__c", "")
        if place not in location_map:
            continue
        venue, prefecture, address = location_map[place]
        start = str(event.get("StartTime__c", ""))[:10]
        end = str(event.get("EndTime__c", ""))[:10]
        if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", start) or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", end):
            continue
        source_url = unquote(event.get("URL__c", ""))
        if not source_url:
            continue
        title = " ".join(filter(None, [event.get("SubTitle__c", ""), event.get("Name__c", "")]))
        results.append(build_candidate(
            title=title,
            venue=venue,
            prefecture=prefecture,
            address=address,
            start_date=start,
            end_date=end,
            source_url=source_url,
            source_name="ソニー αプラザ",
            card_text=json.dumps(event, ensure_ascii=False, sort_keys=True),
        ))
    return unique_sources(results)


def parse_nikon(html: str) -> list[dict]:
    soup = BeautifulSoup(html, "html.parser")
    venue_map = {
        "ニコンサロン(ニコンプラザ東京)": (
            "ニコンサロン", "東京都", "東京都新宿区西新宿1-6-1 新宿エルタワー28階",
        ),
        "ニコンプラザ東京 THE GALLERY": (
            "ニコンプラザ東京 THE GALLERY", "東京都", "東京都新宿区西新宿1-6-1 新宿エルタワー28階",
        ),
        "ニコンプラザ大阪 THE GALLERY": (
            "ニコンプラザ大阪 THE GALLERY", "大阪府", "大阪府大阪市中央区博労町3-5-1 御堂筋グランタワー17階",
        ),
    }
    results = []
    for card in soup.select("li.item-event"):
        link = card.select_one("a.item-inner[href]")
        title_node = card.select_one(".is-title.is-name")
        venue_node = card.select_one(".icon-wrap .icon")
        date_node = card.select_one("time.day[data-start][data-end]")
        if not link or not title_node or not venue_node or not date_node:
            continue
        venue_label = normalize(venue_node.get_text(" ", strip=True))
        if venue_label not in venue_map:
            continue
        venue, prefecture, address = venue_map[venue_label]
        start = date_node.get("data-start", "")[:10].replace("/", "-")
        end = date_node.get("data-end", "")[:10].replace("/", "-")
        url = urljoin("https://nij.nikon.com", link.get("href", ""))
        results.append(build_candidate(
            title=normalize(title_node.get_text(" ", strip=True)),
            venue=venue,
            prefecture=prefecture,
            address=address,
            start_date=start,
            end_date=end,
            source_url=url,
            source_name="ニコンプラザ写真展",
            card_text=card.get_text(" ", strip=True),
        ))
    return unique_sources(results)


def parse_leica(html: str) -> list[dict]:
    soup = BeautifulSoup(html, "html.parser")
    venue_map = {
        "Leica Gallery Tokyo": ("ライカギャラリー東京", "東京都", "東京都中央区銀座6-4-1 2F"),
        "Leica Gallery Omotesando": ("ライカギャラリー表参道", "東京都", "東京都渋谷区神宮前5-16-15 2F"),
        "Leica Gallery Kyoto": ("ライカギャラリー京都", "京都府", "京都府京都市東山区祇園町南側570-120 2F"),
    }
    results = []
    for card in soup.select(".node--events-overview"):
        title_node = card.select_one(".card_headline_info__headline")
        info = [normalize(node.get_text(" ", strip=True)) for node in card.select(".card__event-info__item")]
        link = card.select_one("a[href]")
        if not title_node or not link or len(info) < 3 or info[1] != "日本" or info[2] not in venue_map:
            continue
        dates = dates_from_text(info[0])
        if not dates:
            continue
        venue, prefecture, address = venue_map[info[2]]
        results.append(build_candidate(
            title=title_node.get_text(" ", strip=True),
            venue=venue,
            prefecture=prefecture,
            address=address,
            start_date=dates[0],
            end_date=dates[1],
            source_url=urljoin("https://leica-camera.com", link.get("href", "")),
            source_name="ライカイベント",
            card_text=card.get_text(" ", strip=True),
        ))
    return unique_sources(results)


def parse_kenko(html: str) -> list[dict]:
    soup = BeautifulSoup(html, "html.parser")
    results = []
    for card in soup.select("section.gal-02 ul.gal-list li.clickable"):
        title_node = card.select_one("h3.name")
        date_node = card.select_one("p.date")
        link = card.select_one("a.bt[href]")
        if not title_node or not date_node or not link:
            continue
        dates = dates_from_text(date_node.get_text(" ", strip=True))
        if not dates:
            continue
        results.append(build_candidate(
            title=title_node.get_text(" ", strip=True),
            venue="ケンコー・トキナーギャラリー",
            prefecture="東京都",
            address="東京都中野区中野5-68-10 KT中野ビル2F",
            start_date=dates[0],
            end_date=dates[1],
            source_url=urljoin("https://www.kenko-tokina.co.jp/gallery/", link.get("href", "")),
            source_name="ケンコー・トキナーギャラリー",
            card_text=card.get_text(" ", strip=True),
        ))
    return unique_sources(results)


def parse_topmuseum(html: str) -> list[dict]:
    soup = BeautifulSoup(html, "html.parser")
    results = []
    for card in soup.select(".slider__item"):
        link = card.select_one("a[href]")
        title_node = card.select_one("dt .main")
        description = card.select_one("dd")
        floor_node = description.select_one("em") if description else None
        if not link or not title_node or not description or not floor_node:
            continue
        floor = normalize(floor_node.get_text(" ", strip=True))
        if "展示室" not in floor:
            continue
        dates = dates_from_text(description.get_text(" ", strip=True))
        if not dates:
            continue
        subtitle = card.select_one("dt .sub")
        title = " ".join(filter(None, [
            title_node.get_text(" ", strip=True),
            subtitle.get_text(" ", strip=True) if subtitle else "",
        ]))
        results.append(build_candidate(
            title=title,
            venue=f"東京都写真美術館 {floor}",
            prefecture="東京都",
            address="東京都目黒区三田1-13-3 恵比寿ガーデンプレイス内",
            start_date=dates[0],
            end_date=dates[1],
            source_url=urljoin("https://topmuseum.jp", link.get("href", "")),
            source_name="東京都写真美術館",
            card_text=card.get_text(" ", strip=True),
        ))
    return unique_sources(results)


def parse_om_system(html: str) -> list[dict]:
    pairs = re.findall(
        r'\\"href\\":\\"(https://note\.com/omsystem_plaza/n/[^?\\"]+)[^\\"]*'
        r'\\",\\"title\\":\\"([^\\"]+)',
        html,
    )
    results = []
    for url, full_title in pairs:
        dates = dates_from_text(full_title)
        if not dates:
            continue
        title = re.sub(r"^\s*\d{4}年\d{1,2}月\d{1,2}日[^～〜~]*[～〜~]\s*\d{1,2}月\d{1,2}日[^）)]*[）)]\s*", "", full_title)
        results.append(build_candidate(
            title=title,
            venue="OM SYSTEM GALLERY",
            prefecture="東京都",
            address="東京都新宿区西新宿1-24-1 エステック情報ビルB1F",
            start_date=dates[0],
            end_date=dates[1],
            source_url=url,
            source_name="OM SYSTEM GALLERY",
            card_text=full_title,
        ))
    return unique_sources(results)


def parse_leofoto(html: str) -> list[dict]:
    try:
        posts = json.loads(html)
    except json.JSONDecodeError:
        return []
    results = []
    for post in posts:
        content = BeautifulSoup(post.get("content", {}).get("rendered", ""), "html.parser").get_text(" ", strip=True)
        range_match = re.search(
            r"(?P<sm>\d{1,2})/(?P<sd>\d{1,2})[^~～〜]{0,15}[~～〜]\s*"
            r"(?P<em>\d{1,2})/(?P<ed>\d{1,2})",
            content,
        )
        dates = None
        if range_match:
            year = int(str(post.get("date", ""))[:4])
            start_month = int(range_match.group("sm"))
            end_month = int(range_match.group("em"))
            end_year = year + 1 if end_month < start_month else year
            dates = (
                f"{year:04d}-{start_month:02d}-{int(range_match.group('sd')):02d}",
                f"{end_year:04d}-{end_month:02d}-{int(range_match.group('ed')):02d}",
            )
        if not dates or "写真展" not in content:
            continue
        title = BeautifulSoup(post.get("title", {}).get("rendered", ""), "html.parser").get_text(" ", strip=True)
        title = re.sub(r"^【イベント情報】\s*", "", title)
        title = re.sub(r"^\d{1,2}/\d{1,2}[^~～〜]*[~～〜]\s*", "", title)
        title = re.sub(r"\s*開催のお知らせ\s*$", "", title)
        results.append(build_candidate(
            title=title,
            venue="Leofoto/Summit Creativeショールーム",
            prefecture="埼玉県",
            address="埼玉県川口市西川口3-33-29 NWビル2F",
            start_date=dates[0],
            end_date=dates[1],
            source_url=post.get("link", ""),
            source_name="Leofotoショールーム",
            card_text=content,
        ))
    return unique_sources(results)


def parse_fotori(html: str) -> list[dict]:
    soup = BeautifulSoup(html, "html.parser")
    results = []
    for link in soup.select(".entry-content a[href*='fotori.net/?p=']"):
        title = normalize(link.get_text(" ", strip=True))
        if not title or not any(word in title for word in ("展", "写真")):
            continue
        dates = dates_from_text(title)
        if not dates:
            continue
        clean_title = re.sub(r"^\d{1,2}/\d{1,2}[^~〜～–—]*[~〜～–—]\s*(?:\d{1,2}/)?\d{1,2}[^）)]*[）)]\s*", "", title)
        results.append(build_candidate(
            title=clean_title,
            venue="写真企画室 ホトリ",
            prefecture="東京都",
            address="東京都台東区浅草橋5-2-10",
            start_date=dates[0],
            end_date=dates[1],
            source_url=link.get("href", ""),
            source_name="写真企画室 ホトリ",
            card_text=title,
        ))
    return unique_sources(results)


def parse_shadai(html: str) -> list[dict]:
    soup = BeautifulSoup(html, "html.parser")
    results = []
    for card in soup.select("a.archive_div_a[href]"):
        title_node = card.select_one("h3.jp")
        date_node = card.select_one("p.en.h3")
        if not title_node or not date_node:
            continue
        dates = english_dates_from_text(date_node.get_text(" ", strip=True))
        if not dates:
            continue
        results.append(build_candidate(
            title=title_node.get_text(" ", strip=True),
            venue="東京工芸大学 写大ギャラリー",
            prefecture="東京都",
            address="東京都中野区本町2-4-7 東京工芸大学5号館2F",
            start_date=dates[0],
            end_date=dates[1],
            source_url=card.get("href", ""),
            source_name="写大ギャラリー",
            card_text=card.get_text(" ", strip=True),
        ))
    return unique_sources(results)


def parse_placem(html: str) -> list[dict]:
    soup = BeautifulSoup(html, "html.parser")
    results = []
    for row in soup.select("table tr"):
        link = row.select_one("a[href]")
        if not link:
            continue
        dates = dates_from_text(row.get_text(" ", strip=True))
        if not dates:
            continue
        results.append(build_candidate(
            title=link.get_text(" ", strip=True),
            venue="Place M",
            prefecture="東京都",
            address="東京都新宿区新宿1-2-11 近代ビル3F",
            start_date=dates[0],
            end_date=dates[1],
            source_url=urljoin("https://placem.com/schedule/schedule.php", link.get("href", "")),
            source_name="Place M",
            card_text=row.get_text(" ", strip=True),
        ))
    return unique_sources(results)


def parse_photographers_gallery(html: str) -> list[dict]:
    soup = BeautifulSoup(html, "html.parser")
    results = []
    for card in soup.select("a.post[href]"):
        title_node = card.select_one(".title")
        date_node = card.select_one(".date")
        if not title_node or not date_node:
            continue
        dates = dates_from_text(date_node.get_text(" ", strip=True))
        if not dates:
            continue
        results.append(build_candidate(
            title=title_node.get_text(" ", strip=True),
            venue="photographers’ gallery",
            prefecture="東京都",
            address="東京都新宿区新宿2-16-11 サンフタミビル4F",
            start_date=dates[0],
            end_date=dates[1],
            source_url=card.get("href", ""),
            source_name="photographers’ gallery",
            card_text=card.get_text(" ", strip=True),
        ))
    return unique_sources(results)


def parse_zen_foto(html: str) -> list[dict]:
    soup = BeautifulSoup(html, "html.parser")
    results = []
    for card in soup.select("article"):
        title_node = card.select_one("h3")
        link = card.select_one("a[href*='/exhibition/']")
        if not title_node or not link:
            continue
        dates = dates_from_text(card.get_text(" ", strip=True))
        if not dates:
            continue
        results.append(build_candidate(
            title=title_node.get_text(" ", strip=True),
            venue="ZEN FOTO GALLERY",
            prefecture="東京都",
            address="東京都港区六本木6-6-9 ピラミデビル208号室",
            start_date=dates[0],
            end_date=dates[1],
            source_url=urljoin("https://zen-foto.jp", link.get("href", "")),
            source_name="ZEN FOTO GALLERY",
            card_text=card.get_text(" ", strip=True),
        ))
    return unique_sources(results)


def parse_roonee(html: str) -> list[dict]:
    soup = BeautifulSoup(html, "html.parser")
    cards = list(soup.select("article.exhbtn"))
    upcoming = soup.select_one("article.upcmng")
    if upcoming:
        cards.extend(upcoming.select(":scope > div"))
    results = []
    for card in cards:
        title_node = card.select_one("h2, h3")
        link = card.select_one("a[href]")
        if not title_node or not link:
            continue
        dates = dates_from_text(card.get_text(" ", strip=True))
        if not dates:
            continue
        room_node = card.select_one(".details > span")
        if not room_node:
            room_node = next((node for node in card.select("p") if "Room" in node.get_text() or "wall" in node.get_text()), None)
        room = room_node.get_text(" ", strip=True) if room_node else ""
        results.append(build_candidate(
            title=title_node.get_text(" ", strip=True),
            venue=f"Roonee 247 Fine Arts {room}".strip(),
            prefecture="東京都",
            address="東京都中央区日本橋小伝馬町17-9 さとうビルB館4F",
            start_date=dates[0],
            end_date=dates[1],
            source_url=link.get("href", ""),
            source_name="Roonee 247 Fine Arts",
            card_text=card.get_text(" ", strip=True),
        ))
    return unique_sources(results)


def parse_tosei(html: str) -> list[dict]:
    soup = BeautifulSoup(html, "html.parser")
    results = []
    for cell in soup.select("td.j12"):
        link = cell.select_one("a[href^='j_'][href$='.html']")
        text = cell.get_text(" ", strip=True)
        if not link or "Coming Soon" in text:
            continue
        dates = dates_from_text(text)
        date_match = re.search(r"20\d{2}年\d{1,2}月\d{1,2}日", text)
        if not dates or not date_match:
            continue
        title = text[:date_match.start()].strip()
        results.append(build_candidate(
            title=title,
            venue="ギャラリー冬青",
            prefecture="東京都",
            address="東京都中野区中央5-18-20",
            start_date=dates[0],
            end_date=dates[1],
            source_url=urljoin(
                "https://www.tosei-sha.jp/TOSEI-NEW-HP/html/EXHIBITIONS/j_exhibitions.html",
                link.get("href", ""),
            ),
            source_name="ギャラリー冬青",
            card_text=text,
        ))
    return unique_sources(results)


def unique_sources(candidates: list[dict]) -> list[dict]:
    return list({candidate["source"]["key"]: candidate for candidate in candidates}.values())


def active_candidates(candidates: list[dict]) -> list[dict]:
    today = date.today().isoformat()
    return [
        candidate for candidate in candidates
        if candidate["extracted"]["end_date"] >= today
        and candidate["extracted"]["end_date"] >= candidate["extracted"]["start_date"]
    ]


SITES = {
    "fujifilm": SiteDefinition("https://fujifilmsquare.jp/event.html", "フジフイルム スクエア", parse_fujifilm),
    "fujifilm-sapporo": SiteDefinition(
        "https://www.fujifilm.co.jp/photosalon/sapporo/", "富士フイルムフォトサロン 札幌",
        fujifilm_regional_parser(
            venue="富士フイルムフォトサロン 札幌", prefecture="北海道",
            address="北海道札幌市中央区大通西6丁目1 富士フイルム札幌ビル1F",
            base_url="https://www.fujifilm.co.jp/photosalon/sapporo/",
        ),
    ),
    "fujifilm-nagoya": SiteDefinition(
        "https://www.fujifilm.co.jp/photosalon/nagoya/", "富士フイルムフォトサロン 名古屋",
        fujifilm_regional_parser(
            venue="富士フイルムフォトサロン 名古屋", prefecture="愛知県",
            address="愛知県名古屋市中区栄1-12-17 富士フイルム名古屋ビル1F",
            base_url="https://www.fujifilm.co.jp/photosalon/nagoya/",
        ),
    ),
    "fujifilm-osaka": SiteDefinition(
        "https://www.fujifilm.co.jp/photosalon/osaka/", "富士フイルムフォトサロン 大阪",
        fujifilm_regional_parser(
            venue="富士フイルムフォトサロン 大阪", prefecture="大阪府",
            address="大阪府大阪市中央区本町2-5-7 メットライフ本町スクエア1F",
            base_url="https://www.fujifilm.co.jp/photosalon/osaka/",
        ),
    ),
    "canon": SiteDefinition("https://personal.canon.jp/showroom/gallery", "キヤノンギャラリー", parse_canon),
    "sony": SiteDefinition("https://www.sony.jp/camera/imaging-gallery/", "Sony Imaging Gallery", parse_sony, "cp932"),
    "sony-alpha-plaza": SiteDefinition("https://www.sony.jp/function/event/data/aplaza.json", "ソニー αプラザ", parse_sony_alpha_plaza),
    "jcii": SiteDefinition("https://www.jcii-cameramuseum.jp/photosalon/photo-exhibition/", "JCIIフォトサロン", parse_jcii),
    "nikon-salon": SiteDefinition("https://nij.nikon.com/ajax/enjoy/nikonplaza/photoex/plaza_photoplace/salon", "ニコンサロン", parse_nikon),
    "nikon-tokyo": SiteDefinition("https://nij.nikon.com/ajax/enjoy/nikonplaza/photoex/plaza_photoplace/tokyo_gallery", "ニコンプラザ東京 THE GALLERY", parse_nikon),
    "nikon-osaka": SiteDefinition("https://nij.nikon.com/ajax/enjoy/nikonplaza/photoex/plaza_photoplace/osaka_gallery", "ニコンプラザ大阪 THE GALLERY", parse_nikon),
    "leica": SiteDefinition("https://leica-camera.com/ja-JP/leica-event", "ライカギャラリー", parse_leica),
    "kenko": SiteDefinition("https://www.kenko-tokina.co.jp/gallery/", "ケンコー・トキナーギャラリー", parse_kenko),
    "topmuseum": SiteDefinition("https://topmuseum.jp/", "東京都写真美術館", parse_topmuseum),
    "om-system": SiteDefinition("https://note.com/omsystem_plaza/m/m63fa0ad6a296", "OM SYSTEM GALLERY", parse_om_system),
    "leofoto": SiteDefinition("https://leofoto.co.jp/wp-json/wp/v2/posts?search=%E5%86%99%E7%9C%9F%E5%B1%95&per_page=50", "Leofotoショールーム", parse_leofoto),
    "fotori": SiteDefinition("https://fotori.net/?page_id=292", "写真企画室 ホトリ", parse_fotori, "utf-8"),
    "shadai": SiteDefinition("https://www.shadai.t-kougei.ac.jp/annual-schedule/", "東京工芸大学 写大ギャラリー", parse_shadai, "utf-8"),
    "placem": SiteDefinition("https://placem.com/schedule/schedule.php", "Place M", parse_placem, "utf-8"),
    "photographers-gallery": SiteDefinition("https://pg-web.net/exhibition/", "photographers’ gallery", parse_photographers_gallery, "utf-8"),
    "zen-foto": SiteDefinition("https://zen-foto.jp/jp/exhibitions", "ZEN FOTO GALLERY", parse_zen_foto, "utf-8"),
    "roonee": SiteDefinition("https://www.roonee.jp/exhibition/", "Roonee 247 Fine Arts", parse_roonee, "utf-8"),
    "tosei": SiteDefinition(
        "https://www.tosei-sha.jp/TOSEI-NEW-HP/html/EXHIBITIONS/j_exhibitions.html",
        "ギャラリー冬青", parse_tosei, "cp932",
    ),
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

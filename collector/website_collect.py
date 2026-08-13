from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
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
    notes: str | None = None,
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
        "notes": notes,
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
    numeric_range = re.search(
        r"(?P<sy>20\d{2})[./](?P<sm>\d{1,2})[./](?P<sd>\d{1,2})"
        r"[^~〜～–—-]{0,20}[~〜～–—-]\s*"
        r"(?:(?P<ey>20\d{2})[./])?(?P<em>\d{1,2})[./](?P<ed>\d{1,2})",
        normalized,
    )
    if numeric_range:
        return (
            f"{int(numeric_range.group('sy')):04d}-{int(numeric_range.group('sm')):02d}-{int(numeric_range.group('sd')):02d}",
            f"{int(numeric_range.group('ey') or numeric_range.group('sy')):04d}-{int(numeric_range.group('em')):02d}-{int(numeric_range.group('ed')):02d}",
        )
    normalized = re.sub(
        r"(20\d{2})[./](\d{1,2})[./](\d{1,2})",
        lambda match: f"{match.group(1)}年{match.group(2)}月{match.group(3)}日",
        normalized,
    )
    slash_range = re.search(
        r"(?<!\d)(?P<sm>\d{1,2})/(?P<sd>\d{1,2})[^~〜～–—\-]{0,20}[~〜～–—\-]\s*"
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
        if end < start:
            start_year = int(start[:4])
            inferred_end_year = start_year + (1 if end[5:7] < start[5:7] else 0)
            end = f"{inferred_end_year:04d}-{end[5:]}"
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


def parse_monography(html: str) -> list[dict]:
    marker = "window.__BOOTSTRAP_STATE__ = "
    if marker not in html:
        return []
    try:
        state, _ = json.JSONDecoder().raw_decode(html.split(marker, 1)[1])
        cells = state["siteData"]["page"]["properties"]["contentAreas"]["userContent"]["content"]["cells"]
    except (json.JSONDecodeError, KeyError, IndexError, TypeError):
        return []

    results = []
    for cell in cells:
        repeatables = cell.get("content", {}).get("properties", {}).get("repeatables", [])
        for item in repeatables:
            ops = item.get("text", {}).get("content", {}).get("quill", {}).get("ops", [])
            card_text = "".join(
                str(op.get("insert", "")) for op in ops if isinstance(op, dict)
            ).strip()
            date_match = re.search(r"20\d{2}年\d{1,2}月\d{1,2}日", card_text)
            dates = dates_from_text(card_text)
            if not date_match or not dates:
                continue
            title = normalize(card_text[:date_match.start()].replace("\n", " "))
            if not title:
                continue
            source_url = f"https://www.monography.shop/2026#exhibition-{text_hash(title)[:12]}"
            results.append(build_candidate(
                title=title,
                venue="MONO GRAPHY Camera & Art",
                prefecture="東京都",
                address="東京都中央区日本橋小伝馬町17-5 7ビル2F",
                start_date=dates[0],
                end_date=dates[1],
                source_url=source_url,
                source_name="MONO GRAPHY Camera & Art",
                card_text=card_text,
            ))
    return unique_sources(results)


def parse_iia_gallery(html: str) -> list[dict]:
    soup = BeautifulSoup(html, "html.parser")
    results = []
    for card in soup.select(".item"):
        title_node = card.select_one(".item--title")
        date_node = card.select_one(".item--desc")
        link = card.select_one("a[href*='/exhibition/']")
        if not title_node or not date_node or not link:
            continue
        card_text = card.get_text(" ", strip=True)
        dates = dates_from_text(date_node.get_text(" ", strip=True))
        if not dates:
            continue
        results.append(build_candidate(
            title=title_node.get_text(" ", strip=True),
            venue="アイアイエーギャラリー",
            prefecture="東京都",
            address="東京都中央区日本橋小伝馬町17-5 7ビル1F",
            start_date=dates[0],
            end_date=dates[1],
            source_url=urljoin("https://iiagallery.com/", link.get("href", "")),
            source_name="アイアイエーギャラリー",
            card_text=card_text,
        ))
    return unique_sources(results)


def parse_red_gallery(html: str) -> list[dict]:
    soup = BeautifulSoup(html, "html.parser")
    results = []
    for row in soup.select("tr"):
        links = row.select("a[href*='/exhibition.php'], a[href*='exhibition.php']")
        dates = dates_from_text(row.get_text(" ", strip=True))
        if not links or not dates:
            continue
        parts = []
        for link in links:
            part = normalize(link.get_text(" ", strip=True))
            if part and part not in parts:
                parts.append(part)
        if not parts:
            continue
        results.append(build_candidate(
            title=" ".join(parts),
            venue="RED Photo Gallery",
            prefecture="東京都",
            address="東京都新宿区新宿1-2-11 近代ビル2F",
            start_date=dates[0], end_date=dates[1],
            source_url=urljoin("https://photogallery.red/schedule.php", links[0].get("href", "")),
            source_name="RED Photo Gallery",
            card_text=row.get_text(" ", strip=True),
        ))
    return unique_sources(results)


def parse_sirius(html: str) -> list[dict]:
    soup = BeautifulSoup(html, "html.parser")
    results = []
    for card in soup.select("article.entry-card"):
        text = normalize(card.get_text(" ", strip=True))
        dates = dates_from_text(text)
        date_match = re.search(r"20\d{2}/\d{1,2}/\d{1,2}", text)
        links = [
            link for link in card.select("a[href*='/tenji/']")
            if link.get_text(" ", strip=True)
        ]
        if not dates or not date_match or not links:
            continue
        title = text[:date_match.start()].strip()
        results.append(build_candidate(
            title=title,
            venue="アイデムフォトギャラリー シリウス",
            prefecture="東京都",
            address="東京都新宿区新宿1-4-10 アイデム本社ビル2F",
            start_date=dates[0], end_date=dates[1],
            source_url=links[0].get("href", ""),
            source_name="アイデムフォトギャラリー シリウス",
            card_text=text,
        ))
    return unique_sources(results)


def parse_niepce(html: str) -> list[dict]:
    soup = BeautifulSoup(html, "html.parser")
    results = []
    range_pattern = re.compile(
        r"^20\d{2}年\d{1,2}月\d{1,2}日(?:\([^)]*\))?\s*[~〜～\-]\s*"
        r"(?:20\d{2}年)?\d{1,2}月\d{1,2}日(?:\([^)]*\))?"
    )
    for card in soup.select("#content_area .j-textWithImage"):
        text = normalize(card.get_text(" ", strip=True))
        dates = dates_from_text(text)
        prefix = range_pattern.search(text)
        if not dates or not prefix:
            continue
        title = text[prefix.end():].strip()
        if not title:
            continue
        results.append(build_candidate(
            title=title,
            venue="ギャラリー・ニエプス",
            prefecture="東京都",
            address="東京都新宿区四谷4-10 メイプル花上2F",
            start_date=dates[0], end_date=dates[1],
            source_url=(
                f"https://www.niepce-tokyo.net/exhibitions/{date.today().year}/"
                f"#exhibition-{text_hash(title)[:12]}"
            ),
            source_name="ギャラリー・ニエプス",
            card_text=text,
        ))
    return unique_sources(results)


def parse_totem_pole(html: str) -> list[dict]:
    soup = BeautifulSoup(html, "html.parser")
    cards = list(soup.select("main article.hentry"))
    cards.extend(soup.select("section.cat-post-widget li.cat-post-item"))
    results = []
    for card in cards:
        text = normalize(card.get_text(" ", strip=True))
        dates = dates_from_text(text)
        date_match = re.search(r"20\d{2}[./]\d{1,2}[./]\d{1,2}", text)
        if not dates or not date_match:
            continue
        title = text[:date_match.start()].strip()
        link = card.select_one("a[href]")
        post_id = card.get("id", "")
        source_url = link.get("href", "") if link else f"https://tppg.jp/current/#{post_id or text_hash(title)[:12]}"
        results.append(build_candidate(
            title=title,
            venue="TOTEM POLE PHOTO GALLERY",
            prefecture="東京都",
            address="東京都新宿区四谷4-22 第二富士川ビル1F",
            start_date=dates[0], end_date=dates[1],
            source_url=source_url,
            source_name="TOTEM POLE PHOTO GALLERY",
            card_text=text,
        ))
    return unique_sources(results)


def parse_nadar(html: str) -> list[dict]:
    soup = BeautifulSoup(html, "html.parser")
    results = []
    for card in soup.select(".post_list .panel-group li"):
        title_node = card.select_one(".ex_title")
        link = card.select_one("a[href]")
        text = normalize(card.get_text(" ", strip=True))
        dates = dates_from_text(text)
        if not title_node or not link or not dates or "休業" in text:
            continue
        results.append(build_candidate(
            title=title_node.get_text(" ", strip=True),
            venue="Nadar 東京／世田谷",
            prefecture="東京都",
            address="東京都世田谷区世田谷1-41-2 スカイコート第3 108",
            start_date=dates[0], end_date=dates[1],
            source_url=link.get("href", ""),
            source_name="Nadar",
            card_text=text,
        ))
    return unique_sources(results)


def parse_nine_gallery(html: str) -> list[dict]:
    soup = BeautifulSoup(html, "html.parser")
    results = []
    for link in soup.select(".p-archive--events-bottom a[href*='/event/exhibition']"):
        text = normalize(link.get_text(" ", strip=True))
        dates = dates_from_text(text)
        title_node = link.select_one(".p-events-loop__item-title")
        if not dates or not title_node:
            continue
        title = re.sub(
            r"^【\d{1,2}/\d{1,2}\s*[-〜～]\s*(?:\d{1,2}/)?\d{1,2}】\s*", "",
            normalize(title_node.get_text(" ", strip=True)),
        )
        results.append(build_candidate(
            title=title,
            venue="Nine Gallery",
            prefecture="東京都",
            address="東京都港区北青山2-10-22 谷・荒井ビル1F",
            start_date=dates[0], end_date=dates[1],
            source_url=link.get("href", ""),
            source_name="Nine Gallery",
            card_text=text,
        ))
    return unique_sources(results)


def parse_fugensha(html: str) -> list[dict]:
    soup = BeautifulSoup(html, "html.parser")
    results = []
    prefix_pattern = re.compile(
        r"^20\d{2}/\d{1,2}/\d{1,2}\s*[（(].{1,3}[)）]\s*[-–—]\s*"
        r"20\d{2}/\d{1,2}/\d{1,2}\s*[（(].{1,3}[)）]\s*"
    )
    for card in soup.select(".events .card.item"):
        text = normalize(card.get_text(" ", strip=True))
        link = card.select_one("a[href]")
        dates = dates_from_text(text)
        prefix = prefix_pattern.search(text)
        if not link or not dates or not prefix or "Exhibition" not in text:
            continue
        title = re.sub(r"\s*Exhibition\s*$", "", text[prefix.end():]).strip()
        results.append(build_candidate(
            title=title,
            venue="ふげん社",
            prefecture="東京都",
            address="東京都目黒区下目黒5-3-12",
            start_date=dates[0], end_date=dates[1],
            source_url=link.get("href", ""),
            source_name="ふげん社",
            card_text=text,
        ))
    return unique_sources(results)


def parse_pgi(html: str) -> list[dict]:
    soup = BeautifulSoup(html, "html.parser")
    results = []
    for card in soup.select(".ex-current-row li.item, .ex-upcoming-row li.item"):
        text = normalize(card.get_text(" ", strip=True))
        dates = dates_from_text(text)
        date_match = re.search(r"20\d{2}[./]\d{1,2}[./]\d{1,2}", text)
        link = card.select_one("a[href*='/exhibitions/']")
        if not dates or not date_match or not link:
            continue
        results.append(build_candidate(
            title=text[:date_match.start()].strip(),
            venue="PGI",
            prefecture="東京都",
            address="東京都港区東麻布2-3-4 TKBビル3F",
            start_date=dates[0], end_date=dates[1],
            source_url=urljoin("https://www.pgi.ac/exhibitions/", link.get("href", "")),
            source_name="PGI",
            card_text=text,
        ))
    return unique_sources(results)


def parse_gallery176(html: str) -> list[dict]:
    soup = BeautifulSoup(html, "html.parser")
    results = []
    for card in soup.select("article.tag-upcoming-exhibitions"):
        text = normalize(card.get_text(" ", strip=True))
        dates = dates_from_text(text)
        title_link = next((
            link for link in card.select("a[href*='/exhibitions/']")
            if link.get_text(" ", strip=True)
        ), None)
        if not dates or not title_link:
            continue
        results.append(build_candidate(
            title=title_link.get_text(" ", strip=True),
            venue="gallery 176",
            prefecture="大阪府",
            address="大阪府豊中市服部元町1-6-1",
            start_date=dates[0], end_date=dates[1],
            source_url=title_link.get("href", ""),
            source_name="gallery 176",
            card_text=text,
        ))
    return unique_sources(results)


def parse_studio35(html: str) -> list[dict]:
    soup = BeautifulSoup(html, "html.parser")
    results = []
    for card in soup.select("article.grid-item.category-exhibition"):
        text = normalize(card.get_text(" ", strip=True))
        dates = dates_from_text(text)
        title_link = next((
            link for link in card.select("a[href*='/exhibition/']")
            if "写真展" in link.get_text(" ", strip=True)
        ), None)
        if not dates or not title_link:
            continue
        results.append(build_candidate(
            title=title_link.get_text(" ", strip=True),
            venue="スタジオ35分",
            prefecture="東京都",
            address="東京都中野区上高田5-47-8",
            start_date=dates[0], end_date=dates[1],
            source_url=title_link.get("href", ""),
            source_name="スタジオ35分",
            card_text=text,
        ))
    return unique_sources(results)


def parse_solaris(html: str) -> list[dict]:
    soup = BeautifulSoup(html, "html.parser")
    results = []
    prefix_pattern = re.compile(
        r"^\d{1,2}/\d{1,2}(?:[（(].{1,3}[)）])?\s*[〜～~\-]\s*"
        r"\d{1,2}/\d{1,2}(?:[（(].{1,3}[)）])?\s*"
    )
    for card in soup.select("article.portfolio_category_44"):
        link = card.select_one(".portfolio_description a[href]")
        if not link:
            continue
        text = normalize(link.get_text(" ", strip=True))
        dates = dates_from_text(text)
        prefix = prefix_pattern.search(text)
        if not dates or not prefix or "休廊" in text or "開催予定" in text:
            continue
        results.append(build_candidate(
            title=text[prefix.end():].strip(),
            venue="ギャラリー・ソラリス",
            prefecture="大阪府",
            address="大阪府大阪市中央区南船場3-2-6 大阪農林会館B1F",
            start_date=dates[0], end_date=dates[1],
            source_url=link.get("href", ""),
            source_name="ギャラリー・ソラリス",
            card_text=text,
        ))
    return unique_sources(results)


def parse_art_gallery_m84(html: str) -> list[dict]:
    soup = BeautifulSoup(html, "html.parser")
    results = []
    for row in soup.select(".entry-content table tr"):
        first_cell = row.find("td")
        if not first_cell:
            continue
        text = normalize(first_cell.get_text(" ", strip=True))
        dates = dates_from_text(text)
        date_match = re.search(r"20\d{2}[./]\d{1,2}[./]\d{1,2}", text)
        if not dates or not date_match:
            continue
        title = text[:date_match.start()].strip()
        if (
            not title
            or any(marker in title for marker in ("休館", "休廊", "貸切"))
            or any(marker in text for marker in ("(仮)", "（仮）", "『仮』", "未定"))
        ):
            continue
        detail_link = next((
            link for link in first_cell.select("a[href]")
            if re.search(r"[?&]p=\d+", link.get("href", ""))
            and "attachment_id" not in link.get("href", "")
        ), None)
        source_url = (
            detail_link.get("href", "") if detail_link
            else f"http://artgallery-m84.com/?page_id=8#event-{text_hash(title)[:12]}"
        )
        results.append(build_candidate(
            title=title,
            venue="Art Gallery M84",
            prefecture="東京都",
            address="東京都中央区銀座4-11-3 ウインド銀座ビル5F",
            start_date=dates[0], end_date=dates[1],
            source_url=source_url,
            source_name="Art Gallery M84",
            card_text=text,
        ))
    return unique_sources(results)


def parse_ig_photo_gallery(html: str) -> list[dict]:
    soup = BeautifulSoup(html, "html.parser")
    results = []
    for heading in soup.select("center h4"):
        if "上映" in normalize(heading.get_text(" ", strip=True)):
            continue
        pieces = []
        exhibition_link = None
        for sibling in heading.next_siblings:
            if getattr(sibling, "name", None) in ("h4", "hr"):
                break
            if getattr(sibling, "get_text", None):
                pieces.append(sibling.get_text(" ", strip=True))
                if exhibition_link is None and hasattr(sibling, "select_one"):
                    if sibling.name == "a" and "exhibition/" in sibling.get("href", ""):
                        exhibition_link = sibling
                    else:
                        exhibition_link = sibling.select_one("a[href*='exhibition/']")
            elif str(sibling).strip():
                pieces.append(str(sibling).strip())
        text = normalize(" ".join(pieces))
        dates = dates_from_text(text)
        if not dates or not exhibition_link:
            continue
        title = normalize(exhibition_link.get_text(" ", strip=True))
        if not title:
            continue
        results.append(build_candidate(
            title=title,
            venue="IG Photo Gallery",
            prefecture="東京都",
            address="東京都中央区銀座3-13-17 辰中ビル3F",
            start_date=dates[0], end_date=dates[1],
            source_url=urljoin("https://www.igpg.jp/", exhibition_link.get("href", "")),
            source_name="IG Photo Gallery",
            card_text=f"{heading.get_text(' ', strip=True)} {text}",
        ))
    return unique_sources(results)


def parse_fuji_photo_gallery_ginza(html: str) -> list[dict]:
    soup = BeautifulSoup(html, "html.parser")
    results = []
    for date_heading in soup.select("h2.c-heading-lv3"):
        date_text = normalize(date_heading.get_text(" ", strip=True))
        dates = dates_from_text(date_text)
        section = date_heading.find_parent("section")
        if not dates or not section:
            continue
        for card in section.select(".c-grid_item"):
            title_node = card.select_one("p.c-heading-lv4")
            if not title_node:
                continue
            title = normalize(title_node.get_text(" ", strip=True))
            spaces = [
                normalize(node.get_text(" ", strip=True))
                for node in card.select(".c-imageBox_labels li")
                if node.get_text(" ", strip=True)
            ]
            venue = "富士フォトギャラリー銀座"
            if spaces:
                venue += "（" + "・".join(spaces) + "）"
            card_text = normalize(f"{date_text} {card.get_text(' ', strip=True)}")
            results.append(build_candidate(
                title=title,
                venue=venue,
                prefecture="東京都",
                address="東京都中央区銀座1-2-4 サクセス銀座ファーストビル4F",
                start_date=dates[0], end_date=dates[1],
                source_url=(
                    "https://www.prolab-create.jp/gallery/ginza/"
                    f"#event-{text_hash(date_text + title)[:12]}"
                ),
                source_name="富士フォトギャラリー銀座",
                card_text=card_text,
            ))
    return unique_sources(results)


def parse_gallery_limelight_ics(ics: str) -> list[dict]:
    unfolded = re.sub(r"\r?\n[ \t]", "", ics)
    results = []
    for block in re.findall(r"BEGIN:VEVENT\r?\n(.*?)\r?\nEND:VEVENT", unfolded, re.DOTALL):
        start_match = re.search(r"^DTSTART(?:;[^:]*)?:(\d{8})", block, re.MULTILINE)
        end_match = re.search(r"^DTEND(?:;[^:]*)?:(\d{8})", block, re.MULTILINE)
        title_match = re.search(r"^SUMMARY:(.*)$", block, re.MULTILINE)
        uid_match = re.search(r"^UID:(.*)$", block, re.MULTILINE)
        if not start_match or not end_match or not title_match:
            continue
        title = re.sub(r"\s+", " ", normalize(
            title_match.group(1)
            .replace(r"\n", " ")
            .replace(r"\,", ",")
            .replace(r"\;", ";")
            .replace(r"\\", "\\")
        )).strip()
        if (
            not title
            or any(marker in title for marker in (
                "予約", "貸し切り", "貸切", "お休み", "休廊", "ご利用あり",
                "タイトル未定", "開催延期", "(仮)", "（仮）", "・仮", "仮・",
            ))
            or title in ("共催展示予定", "展示予定")
        ):
            continue
        start = datetime.strptime(start_match.group(1), "%Y%m%d").date()
        # iCalendar's DTEND is exclusive for all-day events.
        end = datetime.strptime(end_match.group(1), "%Y%m%d").date() - timedelta(days=1)
        if end < start:
            continue
        uid = uid_match.group(1).strip() if uid_match else title
        results.append(build_candidate(
            title=title,
            venue="Gallery LimeLight",
            prefecture="大阪府",
            address="大阪府大阪市住吉区帝塚山中4-1-4",
            start_date=start.isoformat(), end_date=end.isoformat(),
            source_url=(
                "http://gallerylimelight.web.fc2.com/exhibitioncalendarnew.html"
                f"#event-{text_hash(uid)[:12]}"
            ),
            source_name="Gallery LimeLight 展示カレンダー",
            card_text=block,
        ))
    return unique_sources(results)


def parse_gallery_bauhaus(html: str) -> list[dict]:
    soup = BeautifulSoup(html, "html.parser")
    text = re.sub(r"\s+", " ", normalize(soup.get_text(" ", strip=True))).strip()
    current = re.search(
        r"Now Exhibition\s+(?P<title>.{2,300}?)\s+"
        r"会\s*期\s*/?.{0,10}?(?P<dates>20\d{2}年\d{1,2}月\d{1,2}日.{0,40}?"
        r"[~〜～–—-].{0,20}?\d{1,2}月\d{1,2}日)",
        text,
    )
    if not current:
        return []
    dates = dates_from_text(current.group("dates"))
    title = re.sub(r"^(?:Image\s+)+", "", current.group("title")).strip()
    if not dates or not title:
        return []
    detail = next((
        link for link in soup.select("a[href]")
        if re.search(r"/20\d{6}[-/]", link.get("href", ""))
    ), None)
    source_url = (
        urljoin("https://gallerybauhaus.wixsite.com/website/exhibition", detail.get("href", ""))
        if detail else "https://gallerybauhaus.wixsite.com/website/exhibition"
    )
    closure = re.search(
        r"20\d{2}/\d{1,2}/\d{1,2}\s*[~〜～–—-]\s*"
        r"(?:20\d{2}/)?\d{1,2}/\d{1,2}は夏季休廊",
        text,
    )
    return [build_candidate(
        title=title,
        venue="gallery bauhaus",
        prefecture="東京都",
        address="東京都千代田区外神田2-19-14",
        start_date=dates[0], end_date=dates[1],
        source_url=source_url,
        source_name="gallery bauhaus",
        card_text=current.group(0),
        notes=closure.group(0) if closure else None,
    )]


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


def parse_room305(html: str) -> list[dict]:
    marker = "pageJson : "
    if marker not in html:
        return []
    try:
        page, _ = json.JSONDecoder().raw_decode(html.split(marker, 1)[1])
    except (json.JSONDecodeError, IndexError):
        return []
    results = []
    for item in page.get("ListItems", []):
        raw_description = item.get("Description", "")
        description = normalize(raw_description)
        dates = dates_from_text(description)
        if not description or not dates:
            continue
        title = normalize(raw_description.splitlines()[0])
        if title in {"Gallery Room305", "展示スケジュール"}:
            continue
        source_url = f"https://www.gallery-room305.com/schedule#{item.get('Guid', text_hash(title)[:12])}"
        results.append(build_candidate(
            title=title,
            venue="Gallery Room305",
            prefecture="大阪府",
            address="大阪府大阪市都島区片町2-2-64",
            start_date=dates[0],
            end_date=dates[1],
            source_url=source_url,
            source_name="Gallery Room305",
            card_text=description,
        ))
    return unique_sources(results)


def parse_ledeco(html: str) -> list[dict]:
    try:
        root = ET.fromstring(html)
    except ET.ParseError:
        return []
    results = []
    for item in root.findall(".//item"):
        title_node = item.find("title")
        link_node = item.find("link")
        content_node = item.find("{http://purl.org/rss/1.0/modules/content/}encoded")
        categories = [normalize(node.text or "") for node in item.findall("category")]
        if title_node is None or link_node is None or content_node is None or "今週の催事" not in categories:
            continue
        content = BeautifulSoup(content_node.text or "", "html.parser").get_text(" ", strip=True)
        title = normalize(title_node.text or "")
        if not re.search(r"写真|PHOTO|FOTO", f"{title} {content}", re.IGNORECASE):
            continue
        dates = dates_from_text(content)
        if not dates:
            continue
        floors = "・".join(category for category in categories if re.fullmatch(r"[ＢB]?[１-６1-6][ＦF]", category))
        results.append(build_candidate(
            title=title,
            venue=f"ギャラリー・ルデコ {floors}".strip(),
            prefecture="東京都",
            address="東京都渋谷区渋谷3-16-3 高桑ビル",
            start_date=dates[0],
            end_date=dates[1],
            source_url=normalize(link_node.text or ""),
            source_name="ギャラリー・ルデコ",
            card_text=content,
        ))
    return unique_sources(results)


def parse_gallery_owada(html: str) -> list[dict]:
    soup = BeautifulSoup(html, "html.parser")
    grouped: dict[str, dict] = {}
    for day in soup.select(".day.link"):
        date_node = day.select_one("[data-pickup-date]")
        if not date_node:
            continue
        day_value = date_node.get("data-pickup-date", "")
        match = re.fullmatch(r"(20\d{2})-(\d{1,2})-(\d{1,2})", day_value)
        if not match:
            continue
        iso_day = f"{int(match.group(1)):04d}-{int(match.group(2)):02d}-{int(match.group(3)):02d}"
        for link in day.select(".event-list a[href]"):
            title = normalize(link.get_text(" ", strip=True))
            if "写真" not in title:
                continue
            url = link.get("href", "")
            clean_title = re.sub(r"【最終日】$", "", title).strip()
            clean_title = re.sub(r"^\d{1,2}/\d{1,2}\s*[～〜~\-]\s*\d{1,2}\s*", "", clean_title)
            entry = grouped.setdefault(url, {"title": clean_title, "days": [], "text": []})
            entry["days"].append(iso_day)
            entry["text"].append(title)
    return unique_sources([
        build_candidate(
            title=entry["title"],
            venue="ギャラリー大和田",
            prefecture="東京都",
            address="東京都渋谷区桜丘町23-21 渋谷区文化総合センター大和田2F",
            start_date=min(entry["days"]),
            end_date=max(entry["days"]),
            source_url=url,
            source_name="ギャラリー大和田",
            card_text=" ".join(entry["text"]),
        )
        for url, entry in grouped.items()
    ])


def parse_higashikawa(html: str) -> list[dict]:
    soup = BeautifulSoup(html, "html.parser")
    results = []
    for card in soup.select("li.ArticleList__item.category-photo-exhibition, li.ArticleList__item.category-exhibition"):
        link = card.select_one(".ArticleList__title a[href]")
        if not link:
            continue
        text = normalize(card.get_text(" ", strip=True))
        dates = dates_from_text(text)
        if not dates:
            continue
        title = link.get_text(" ", strip=True)
        place_match = re.search(
            r"(?:○)?場所[：:]\s*(.+?)(?=\s+(?:○|レビュ|協力|主催|出展作家|料金|時間|写真|昨年|今年|結成|1985年)|$)",
            text,
        )
        place = place_match.group(1).strip() if place_match else "東川町内各所"
        if "東川賞受賞作家作品展" in title:
            place = "東川町文化ギャラリー"
        results.append(build_candidate(
            title=title,
            venue=place,
            prefecture="北海道",
            start_date=dates[0],
            end_date=dates[1],
            source_url=link.get("href", ""),
            source_name="東川町国際写真フェスティバル",
            card_text=text,
        ))
    return unique_sources(results)


def verified_event_parser(
    *, marker: str, title: str, venue: str, prefecture: str, address: str | None,
    start_date: str, end_date: str, source_url: str, source_name: str,
) -> Callable[[str], list[dict]]:
    def parse(html: str) -> list[dict]:
        text = BeautifulSoup(html, "html.parser").get_text(" ", strip=True)
        if marker not in text:
            return []
        return [build_candidate(
            title=title,
            venue=venue,
            prefecture=prefecture,
            address=address,
            start_date=start_date,
            end_date=end_date,
            source_url=source_url,
            source_name=source_name,
            card_text=f"{title} {start_date} {end_date} {text[:500]}",
        )]
    return parse


def parse_japanese_medium_format_2026(html: str) -> list[dict]:
    text = BeautifulSoup(html, "html.parser").get_text(" ", strip=True)
    if "国産中判フィルム写真展2026" not in text:
        return []
    source = "https://amemiya-hair.tokyo/jpcamera-120film-expo2026/"
    events = [
        (
            "国産中判フィルム写真展 2026（大阪）", "rouleur studio",
            "大阪府大阪市北区天満1-3-3 天馬ビル201", "2026-10-01", "2026-10-04", "osaka",
        ),
        (
            "国産中判フィルム写真展 2026（大阪・特別展示）", "Gallery ANBAI.",
            "大阪府大阪市北区芝田2-1-3 梅仙堂ビル4F", "2026-10-03", "2026-10-04", "anbai",
        ),
    ]
    return [build_candidate(
        title=title, venue=venue, prefecture="大阪府", address=address,
        start_date=start, end_date=end, source_url=f"{source}#{fragment}",
        source_name="国産中判フィルム写真展", card_text=f"{title} {start} {end} {text[:500]}",
    ) for title, venue, address, start, end, fragment in events]


def annual_festival_parser(
    *, marker: str, title_base: str, venue: str, prefecture: str,
    source_url: str, source_name: str,
) -> Callable[[str], list[dict]]:
    def parse(html: str) -> list[dict]:
        text = BeautifulSoup(html, "html.parser").get_text(" ", strip=True)
        marker_position = text.find(marker)
        if marker_position < 0:
            return []
        window = text[marker_position:marker_position + 1500]
        range_match = re.search(
            r"(?P<sy>20\d{2})年\s*(?P<sm>\d{1,2})月\s*(?P<sd>\d{1,2})日"
            r".{0,15}?[～〜~–—-]\s*(?:(?P<ey>20\d{2})年\s*)?"
            r"(?P<em>\d{1,2})月\s*(?P<ed>\d{1,2})日",
            window,
        )
        if range_match:
            start_year = int(range_match.group("sy"))
            start_month = int(range_match.group("sm"))
            end_month = int(range_match.group("em"))
            end_year = int(range_match.group("ey") or start_year + (end_month < start_month))
            dates = (
                f"{start_year:04d}-{start_month:02d}-{int(range_match.group('sd')):02d}",
                f"{end_year:04d}-{end_month:02d}-{int(range_match.group('ed')):02d}",
            )
        else:
            dates = dates_from_text(window)
        if not dates:
            return []
        year = dates[0][:4]
        return [build_candidate(
            title=f"{title_base} {year}", venue=venue, prefecture=prefecture,
            start_date=dates[0], end_date=dates[1], source_url=source_url,
            source_name=source_name, card_text=window,
        )]
    return parse


def calendar_month_url(offset: int) -> str:
    today = date.today()
    month_index = today.year * 12 + today.month - 1 + offset
    year, month_zero = divmod(month_index, 12)
    return f"https://shibu-cul.jp/gallery/calendar?ym={year:04d}-{month_zero + 1:02d}"


def nine_calendar_url(offset: int) -> str:
    today = date.today()
    month_index = today.year * 12 + today.month - 1 + offset
    year, month_zero = divmod(month_index, 12)
    return f"https://ninegallery.com/event/?calender={year:04d}-{month_zero + 1:02d}"


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
    "monography": SiteDefinition(
        "https://www.monography.shop/2026", "MONO GRAPHY Camera & Art", parse_monography, "utf-8",
    ),
    "iia-gallery": SiteDefinition(
        "https://iiagallery.com/", "アイアイエーギャラリー", parse_iia_gallery, "utf-8",
    ),
    "red-gallery": SiteDefinition(
        "https://photogallery.red/schedule.php", "RED Photo Gallery", parse_red_gallery, "utf-8",
    ),
    "sirius": SiteDefinition(
        "https://www.photo-sirius.net/tenji/", "アイデムフォトギャラリー シリウス", parse_sirius, "utf-8",
    ),
    "niepce": SiteDefinition(
        f"https://www.niepce-tokyo.net/exhibitions/{date.today().year}/",
        "ギャラリー・ニエプス", parse_niepce, "utf-8",
    ),
    "totem-pole": SiteDefinition(
        "https://tppg.jp/current/", "TOTEM POLE PHOTO GALLERY", parse_totem_pole, "utf-8",
    ),
    "nadar": SiteDefinition(
        "https://g-nadar.net/gallery/ex_new", "Nadar 東京／世田谷", parse_nadar, "utf-8",
    ),
    "nine-current": SiteDefinition(
        nine_calendar_url(0), "Nine Gallery（今月）", parse_nine_gallery, "utf-8",
    ),
    "nine-next": SiteDefinition(
        nine_calendar_url(1), "Nine Gallery（翌月）", parse_nine_gallery, "utf-8",
    ),
    "fugensha": SiteDefinition(
        "https://fugensha.jp/", "ふげん社", parse_fugensha, "utf-8",
    ),
    "pgi": SiteDefinition(
        "https://www.pgi.ac/exhibitions/", "PGI", parse_pgi, "utf-8",
    ),
    "gallery176": SiteDefinition(
        "https://176.photos/tag/upcoming-exhibitions/", "gallery 176", parse_gallery176, "utf-8",
    ),
    "studio35": SiteDefinition(
        "https://35fn.com/category/exhibition/", "スタジオ35分", parse_studio35, "utf-8",
    ),
    "solaris": SiteDefinition(
        "https://solaris-g.com/exhibition/", "ギャラリー・ソラリス", parse_solaris, "utf-8",
    ),
    "art-gallery-m84": SiteDefinition(
        "http://artgallery-m84.com/?page_id=8", "Art Gallery M84", parse_art_gallery_m84, "utf-8",
    ),
    "ig-photo-gallery": SiteDefinition(
        "https://www.igpg.jp/", "IG Photo Gallery", parse_ig_photo_gallery, "utf-8",
    ),
    "fuji-photo-gallery-ginza": SiteDefinition(
        "https://www.prolab-create.jp/gallery/ginza/", "富士フォトギャラリー銀座",
        parse_fuji_photo_gallery_ginza, "utf-8",
    ),
    "gallery-limelight": SiteDefinition(
        "https://calendar.google.com/calendar/ical/"
        "mikk03itcr95ncl2ml14j3gue0%40group.calendar.google.com/public/basic.ics",
        "Gallery LimeLight", parse_gallery_limelight_ics, "utf-8",
    ),
    "gallery-bauhaus": SiteDefinition(
        "https://gallerybauhaus.wixsite.com/website/exhibition", "gallery bauhaus",
        parse_gallery_bauhaus, "utf-8",
    ),
    "tosei": SiteDefinition(
        "https://www.tosei-sha.jp/TOSEI-NEW-HP/html/EXHIBITIONS/j_exhibitions.html",
        "ギャラリー冬青", parse_tosei, "cp932",
    ),
    "room305": SiteDefinition(
        "https://www.gallery-room305.com/schedule", "Gallery Room305", parse_room305, "utf-8",
    ),
    "ledeco": SiteDefinition(
        "https://ledeco.net/?feed=rss2&cat=5", "ギャラリー・ルデコ", parse_ledeco, "utf-8",
    ),
    "gallery-owada-current": SiteDefinition(
        calendar_month_url(0), "ギャラリー大和田（今月）", parse_gallery_owada, "utf-8",
    ),
    "gallery-owada-next": SiteDefinition(
        calendar_month_url(1), "ギャラリー大和田（翌月）", parse_gallery_owada, "utf-8",
    ),
    "higashikawa": SiteDefinition(
        "https://photo-town.jp/schedule/", "東川町国際写真フェスティバル", parse_higashikawa, "utf-8",
    ),
    "asama-photo-festival": SiteDefinition(
        "https://asamaphotofes.jp/", "浅間国際フォトフェスティバル",
        verified_event_parser(
            marker="浅間国際フォトフェスティバル2026 PHOTO MIYOTA",
            title="浅間国際フォトフェスティバル2026 PHOTO MIYOTA",
            venue="MMoPほか御代田町内各所", prefecture="長野県",
            address="長野県北佐久郡御代田町馬瀬口1794-1",
            start_date="2026-08-01", end_date="2026-09-27",
            source_url="https://asamaphotofes.jp/", source_name="浅間国際フォトフェスティバル",
        ), "utf-8",
    ),
    "t3-photo-festival": SiteDefinition(
        "https://prtimes.jp/main/html/rd/p/000000015.000085103.html", "T3 PHOTO FESTIVAL TOKYO",
        verified_event_parser(
            marker="T3 PHOTO FESTIVAL TOKYO 2026",
            title="T3 PHOTO FESTIVAL TOKYO 2026",
            venue="八重洲・日本橋・京橋・銀座エリア各所", prefecture="東京都", address=None,
            start_date="2026-10-03", end_date="2026-10-26",
            source_url="https://t3photo.tokyo/", source_name="T3 PHOTO FESTIVAL TOKYO",
        ), "utf-8",
    ),
    "tokyo-camera-club-2026": SiteDefinition(
        "https://tokyocameraclub.com/special/exhibition_2026/", "東京カメラ部2026写真展",
        verified_event_parser(
            marker="東京カメラ部2026写真展",
            title="東京カメラ部2026写真展「ひろがる世界。」",
            venue="渋谷ヒカリエ 9F ヒカリエホール ホールAB", prefecture="東京都",
            address="東京都渋谷区渋谷2-21-1",
            start_date="2026-09-19", end_date="2026-09-22",
            source_url="https://tokyocameraclub.com/special/exhibition_2026/",
            source_name="東京カメラ部2026写真展",
        ), "utf-8",
    ),
    "kyotographie-2027": SiteDefinition(
        "https://www.kyotographie.jp/", "KYOTOGRAPHIE 京都国際写真祭",
        verified_event_parser(
            marker="2027.04.17 - 05.16",
            title="KYOTOGRAPHIE 京都国際写真祭 2027",
            venue="京都市内各所", prefecture="京都府", address=None,
            start_date="2027-04-17", end_date="2027-05-16",
            source_url="https://www.kyotographie.jp/", source_name="KYOTOGRAPHIE 京都国際写真祭",
        ), "utf-8",
    ),
    "japanese-medium-format-2026": SiteDefinition(
        "https://amemiya-hair.tokyo/jpcamera-120film-expo2026/", "国産中判フィルム写真展2026",
        parse_japanese_medium_format_2026, "utf-8",
    ),
    "10p10fp-2026": SiteDefinition(
        "https://10p10fp10.studio.site/", "10p10fp展2026",
        verified_event_parser(
            marker="10p10fp展2026",
            title="10p10fp展2026", venue="建築会館ギャラリー", prefecture="東京都",
            address="東京都港区芝5-26-20",
            start_date="2026-10-31", end_date="2026-11-03",
            source_url="https://10p10fp10.studio.site/", source_name="10p10fp展",
        ), "utf-8",
    ),
    "shiogama-photo-festival": SiteDefinition(
        "https://sgma.jp/", "塩竈フォトフェスティバル",
        annual_festival_parser(
            marker="塩竈フォトフェスティバル", title_base="塩竈フォトフェスティバル",
            venue="塩竈市内各所", prefecture="宮城県",
            source_url="https://sgma.jp/", source_name="塩竈フォトフェスティバル",
        ), "utf-8",
    ),
    "yakushima-photo-festival": SiteDefinition(
        "https://www.ypf.photos/", "屋久島国際写真祭",
        annual_festival_parser(
            marker="屋久島国際写真祭", title_base="屋久島国際写真祭",
            venue="屋久島島内各所", prefecture="鹿児島県",
            source_url="https://www.ypf.photos/", source_name="屋久島国際写真祭",
        ), "utf-8",
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

from __future__ import annotations

import hashlib
import re
import unicodedata
from datetime import datetime
from typing import Any


PREFECTURES = (
    "北海道", "青森県", "岩手県", "宮城県", "秋田県", "山形県", "福島県",
    "茨城県", "栃木県", "群馬県", "埼玉県", "千葉県", "東京都", "神奈川県",
    "新潟県", "富山県", "石川県", "福井県", "山梨県", "長野県", "岐阜県",
    "静岡県", "愛知県", "三重県", "滋賀県", "京都府", "大阪府", "兵庫県",
    "奈良県", "和歌山県", "鳥取県", "島根県", "岡山県", "広島県", "山口県",
    "徳島県", "香川県", "愛媛県", "高知県", "福岡県", "佐賀県", "長崎県",
    "熊本県", "大分県", "宮崎県", "鹿児島県", "沖縄県",
)

CITY_PREFECTURES = {
    "札幌": "北海道", "仙台": "宮城県", "さいたま": "埼玉県", "千葉市": "千葉県",
    "東京": "東京都", "新宿": "東京都", "銀座": "東京都", "池袋": "東京都",
    "横浜": "神奈川県", "川崎": "神奈川県", "名古屋": "愛知県", "京都市": "京都府",
    "大阪": "大阪府", "神戸": "兵庫県", "岡山市": "岡山県", "広島市": "広島県",
    "高松": "香川県", "福岡市": "福岡県", "那覇": "沖縄県",
}

DATE_RANGE_RE = re.compile(
    r"(?:(?P<sy>20\d{2})年)?\s*(?P<sm>\d{1,2})月\s*(?P<sd>\d{1,2})日"
    r"[^\n]{0,30}?[~〜～\-–—]\s*"
    r"(?:(?P<ey>20\d{2})年)?\s*(?:(?P<em>\d{1,2})月\s*)?(?P<ed>\d{1,2})日"
)
SINGLE_DATE_RE = re.compile(r"(?:(?P<year>20\d{2})年)?\s*(?P<month>\d{1,2})月\s*(?P<day>\d{1,2})日")
TITLE_QUOTE_RE = re.compile(r"(?:写真展|個展)\s*[「『\"]([^」』\"]{2,120})[」』\"]")
VENUE_LABEL_RE = re.compile(r"^(?:展示会場|会場|場所)\s*[:：]?\s*(.+)$", re.IGNORECASE)
VENUE_WORD_RE = re.compile(r"ギャラリー|gallery|フォトサロン|サロン|美術館|展示ホール|文化会館|茶館|アートスペース", re.IGNORECASE)
GENERIC_TITLE_RE = re.compile(r"^(?:写真展|個展)(?:に)?(?:出展|開催)?(?:の)?お知らせ|写真展を開催(?:します|中)?$")


def normalize(text: str) -> str:
    return unicodedata.normalize("NFKC", text).replace("\r\n", "\n").replace("\r", "\n")


def clean_line(line: str) -> str:
    return re.sub(r"\s+", " ", line.strip(" \t・📸🖼️-—"))


def inferred_year(month: int, published_at: datetime, explicit: str | None) -> int:
    if explicit:
        return int(explicit)
    year = published_at.year
    if published_at.month >= 10 and month <= 3:
        year += 1
    return year


def iso_date(year: int, month: int, day: int) -> str | None:
    try:
        return datetime(year, month, day).date().isoformat()
    except ValueError:
        return None


def extract_dates(text: str, published_at: datetime) -> tuple[str | None, str | None]:
    text = re.sub(
        r"(20\d{2})/(\d{1,2})/(\d{1,2})",
        lambda match: f"{match.group(1)}年{match.group(2)}月{match.group(3)}日",
        text,
    )
    match = DATE_RANGE_RE.search(text)
    if match:
        start_month = int(match.group("sm"))
        end_month = int(match.group("em") or start_month)
        start_year = inferred_year(start_month, published_at, match.group("sy"))
        if match.group("ey"):
            end_year = int(match.group("ey"))
        elif match.group("sy"):
            end_year = start_year
        else:
            end_year = inferred_year(end_month, published_at, None)
        if end_month < start_month and not match.group("ey"):
            end_year = start_year + 1
        return (
            iso_date(start_year, start_month, int(match.group("sd"))),
            iso_date(end_year, end_month, int(match.group("ed"))),
        )

    dates = list(SINGLE_DATE_RE.finditer(text))
    if not dates:
        return None, None

    first = dates[0]
    month = int(first.group("month"))
    value = iso_date(
        inferred_year(month, published_at, first.group("year")),
        month,
        int(first.group("day")),
    )
    nearby = text[first.end():first.end() + 12]
    if "まで" in nearby or "終了" in text[max(0, first.start() - 8):first.start()]:
        return None, value
    return value, value


def extract_title(lines: list[str]) -> str | None:
    joined = "\n".join(lines)
    quoted = TITLE_QUOTE_RE.search(joined)
    if quoted:
        return clean_line(quoted.group(1))

    candidates: list[tuple[int, str]] = []
    for line in lines:
        cleaned = clean_line(line)
        if not 3 <= len(cleaned) <= 180:
            continue
        if "写真展" not in cleaned and "個展" not in cleaned:
            continue
        score = 0
        if "写真展" in cleaned:
            score += 3
        if any(mark in cleaned for mark in ("「", "『", "【", "~", "〜")):
            score += 2
        if GENERIC_TITLE_RE.search(cleaned) or len(cleaned) > 120:
            score -= 4
        if any(word in cleaned for word in ("日時", "会期", "会場", "場所")):
            score -= 2
        candidates.append((score, cleaned))

    if candidates:
        candidates.sort(key=lambda item: (-item[0], len(item[1])))
        if candidates[0][0] >= 0:
            return candidates[0][1]

    for line in lines:
        match = re.search(r"【([^】]{2,100})】", line)
        if match:
            return clean_line(match.group(1))
    return None


def extract_venue(lines: list[str]) -> str | None:
    for line in lines:
        match = VENUE_LABEL_RE.match(clean_line(line))
        if match:
            value = clean_line(match.group(1))
            value = re.split(r"(?:会期時間|日時|時間)\s*[:：]", value)[0]
            return value[:300] or None

    for line in lines:
        cleaned = clean_line(line)
        if VENUE_WORD_RE.search(cleaned) and len(cleaned) <= 180 and "写真展" not in cleaned:
            cleaned = re.sub(r"^(?:大阪|東京|京都|横浜)[・･\s]*", "", cleaned)
            return cleaned[:300]
    return None


def extract_prefecture(text: str) -> str | None:
    for prefecture in PREFECTURES:
        if prefecture in text:
            return prefecture
    for city, prefecture in CITY_PREFECTURES.items():
        if city in text:
            return prefecture
    return None


def extract_address(lines: list[str]) -> str | None:
    for line in lines:
        cleaned = clean_line(line)
        if any(prefecture in cleaned for prefecture in PREFECTURES):
            return cleaned[:500]
    return None


def fingerprint(extracted: dict[str, Any], source_key: str) -> str:
    values = [
        str(extracted.get("title") or ""),
        str(extracted.get("venue") or ""),
        str(extracted.get("start_date") or ""),
        str(extracted.get("end_date") or ""),
    ]
    populated = sum(bool(value) for value in values)
    basis = "|".join(normalize(value).lower().replace(" ", "") for value in values)
    if populated < 3:
        basis = f"source|{source_key}"
    return hashlib.sha256(basis.encode("utf-8")).hexdigest()


def extract_event(text: str, published_at: datetime, source_key: str) -> dict[str, Any]:
    normalized = normalize(text)
    lines = [line for raw in normalized.split("\n") if (line := clean_line(raw))]
    start_date, end_date = extract_dates(normalized, published_at)
    title = extract_title(lines)
    venue = extract_venue(lines)
    prefecture = extract_prefecture(normalized)

    extracted = {
        "title": title,
        "host_name": None,
        "venue": venue,
        "address": extract_address(lines),
        "prefecture": prefecture,
        "price": "無料" if "入場無料" in normalized else None,
        "start_date": start_date,
        "end_date": end_date,
        "notes": None,
    }

    weights = {
        "title": 0.25,
        "venue": 0.20,
        "prefecture": 0.10,
        "start_date": 0.20,
        "end_date": 0.20,
    }
    confidence = 0.05 + sum(weight for field, weight in weights.items() if extracted[field])
    confidence = round(min(confidence, 1.0), 3)

    return {
        "event_fingerprint": fingerprint(extracted, source_key),
        "confidence": confidence,
        "extracted": extracted,
        "content_hash": hashlib.sha256(normalized.encode("utf-8")).hexdigest(),
    }

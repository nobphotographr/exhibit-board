from __future__ import annotations

import argparse
import json
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup

try:
    from .photo_culture_collect import BASE_URL, SOCIAL_HOSTS, clean, parse_gallery_detail
    from .website_collect import USER_AGENT
except ImportError:  # Direct script execution
    from photo_culture_collect import BASE_URL, SOCIAL_HOSTS, clean, parse_gallery_detail
    from website_collect import USER_AGENT


REGISTRY_URL = urljoin(BASE_URL, "gallerylist.php")


@dataclass(frozen=True)
class GalleryRecord:
    name: str
    area: str
    detail_url: str
    address: str | None = None
    official_url: str | None = None
    status: str = "pending"
    reason: str | None = None


def parse_registry(html: str) -> list[GalleryRecord]:
    soup = BeautifulSoup(html, "html.parser")
    records = []
    for row in soup.select("table tr"):
        cells = row.select("td")
        if len(cells) < 2:
            continue
        area = clean(cells[0].get_text(" ", strip=True))
        for link in cells[1].select("a[href*='gallerydet.php?i=']"):
            name = clean(link.get_text(" ", strip=True))
            if name:
                records.append(GalleryRecord(
                    name=name,
                    area=area,
                    detail_url=urljoin(BASE_URL, link.get("href", "")),
                ))
    return records


def audit_record(record: GalleryRecord) -> GalleryRecord:
    try:
        response = requests.get(
            record.detail_url,
            headers={"User-Agent": USER_AGENT},
            timeout=30,
        )
        response.raise_for_status()
        response.encoding = response.apparent_encoding or "utf-8"
        address, official_url = parse_gallery_detail(response.text)
    except requests.RequestException as exc:
        return GalleryRecord(
            **{**asdict(record), "status": "fetch_error", "reason": str(exc)},
        )

    if not official_url:
        status = "no_official_url"
        reason = "Photo & Culture, Tokyoの会場詳細に公式URLの登録なし"
    else:
        host = (urlparse(official_url).hostname or "").removeprefix("www.")
        if host in SOCIAL_HOSTS:
            status = "social_only"
            reason = "登録URLがSNSのみ"
        else:
            status = "official_website"
            reason = None
    return GalleryRecord(
        name=record.name,
        area=record.area,
        detail_url=record.detail_url,
        address=address,
        official_url=official_url,
        status=status,
        reason=reason,
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Audit the Photo & Culture, Tokyo gallery registry")
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    response = requests.get(REGISTRY_URL, headers={"User-Agent": USER_AGENT}, timeout=30)
    response.raise_for_status()
    response.encoding = response.apparent_encoding or "utf-8"
    records = parse_registry(response.text)

    audited: list[GalleryRecord | None] = [None] * len(records)
    with ThreadPoolExecutor(max_workers=max(1, min(args.workers, 8))) as executor:
        jobs = {executor.submit(audit_record, record): index for index, record in enumerate(records)}
        for job in as_completed(jobs):
            audited[jobs[job]] = job.result()

    final_records = [record for record in audited if record is not None]
    summary: dict[str, int] = {}
    for record in final_records:
        summary[record.status] = summary.get(record.status, 0) + 1
    payload = {
        "source": REGISTRY_URL,
        "audited_at": datetime.now(timezone.utc).isoformat(),
        "total": len(final_records),
        "summary": summary,
        "venues": [asdict(record) for record in final_records],
    }
    if args.output:
        args.output.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"total": len(final_records), **summary}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

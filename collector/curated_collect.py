from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from datetime import date
from pathlib import Path
from typing import Any

try:
    from .extract import fingerprint
    from .x_recent_search import load_env, post_candidate
except ImportError:  # Direct script execution
    from extract import fingerprint
    from x_recent_search import load_env, post_candidate


REQUIRED_FIELDS = (
    "title", "venue", "prefecture", "start_date", "end_date", "source",
)


def build_candidate(record: dict[str, Any]) -> dict[str, Any]:
    missing = [field for field in REQUIRED_FIELDS if not record.get(field)]
    if missing:
        raise ValueError(f"curated event is missing: {', '.join(missing)}")

    source = record["source"]
    if not source.get("key") or not source.get("url"):
        raise ValueError("curated event source requires key and url")

    extracted = {
        field: record.get(field)
        for field in (
            "title", "host_name", "venue", "address", "prefecture", "price",
            "start_date", "end_date", "notes",
        )
    }
    normalized = json.dumps(record, ensure_ascii=False, sort_keys=True)
    return {
        "event_fingerprint": fingerprint(extracted, str(source["key"])),
        "confidence": 1.0,
        "extracted": extracted,
        "source": {
            "type": "manual",
            "key": str(source["key"]),
            "url": source["url"],
            "name": source.get("name"),
            "author_handle": source.get("author_handle"),
            "content_hash": hashlib.sha256(normalized.encode("utf-8")).hexdigest(),
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Publish curator-approved photo exhibitions")
    parser.add_argument("--env-file", type=Path, default=Path(".env"))
    parser.add_argument(
        "--events-file", type=Path,
        default=Path(__file__).with_name("curated_events.json"),
    )
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    load_env(args.env_file)
    endpoint = os.environ.get("COLLECTOR_ENDPOINT", "").rstrip("/")
    collector_key = os.environ.get("COLLECTOR_API_KEY", "")
    if not args.dry_run and (not endpoint or not collector_key):
        raise SystemExit("COLLECTOR_ENDPOINT and COLLECTOR_API_KEY are required")

    records = json.loads(args.events_file.read_text(encoding="utf-8")).get("events", [])
    published = 0
    for record in records:
        if date.fromisoformat(record["end_date"]) < date.today():
            continue
        candidate = build_candidate(record)
        if not args.dry_run:
            post_candidate(f"{endpoint}/api/internal/candidates", collector_key, candidate)
        print(json.dumps(candidate, ensure_ascii=False))
        published += 1

    print(f"curated={len(records)} active={published}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

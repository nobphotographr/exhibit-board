from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import requests

try:
    from .extract import extract_event
except ImportError:  # Direct script execution
    from extract import extract_event


SEARCH_URL = "https://api.x.com/2/tweets/search/recent"
DEFAULT_QUERY = (
    '("写真展" OR "写真個展" OR "グループ写真展") '
    '("開催します" OR "展示します" OR "個展を開催" OR "写真展を開催") '
    'lang:ja -is:retweet -is:reply'
)


def load_env(path: Path) -> None:
    if not path.exists():
        return
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip())


def read_state(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def write_state(path: Path, state: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")
    temporary.replace(path)


def search_posts(token: str, query: str, state: dict[str, Any], bootstrap_hours: int) -> dict[str, Any]:
    params = {
        "query": query,
        "max_results": 100,
        "sort_order": "recency",
        "tweet.fields": "created_at,author_id,note_tweet",
        "expansions": "author_id",
        "user.fields": "username,name",
    }
    if state.get("newest_id"):
        params["since_id"] = state["newest_id"]
    else:
        start = datetime.now(timezone.utc) - timedelta(hours=bootstrap_hours)
        params["start_time"] = start.replace(microsecond=0).isoformat().replace("+00:00", "Z")

    response = requests.get(
        SEARCH_URL,
        headers={"Authorization": f"Bearer {token}"},
        params=params,
        timeout=30,
    )
    response.raise_for_status()
    return response.json()


def post_candidate(endpoint: str, api_key: str, candidate: dict[str, Any]) -> None:
    response = requests.post(
        endpoint,
        headers={"Authorization": f"Bearer {api_key}"},
        json=candidate,
        timeout=30,
    )
    response.raise_for_status()


def main() -> int:
    parser = argparse.ArgumentParser(description="Collect Japanese photo exhibition announcements from X")
    parser.add_argument("--env-file", type=Path, default=Path(".env"))
    parser.add_argument("--state-file", type=Path, default=Path(".collector-state.json"))
    parser.add_argument("--bootstrap-hours", type=int, default=6)
    parser.add_argument("--query", default=DEFAULT_QUERY)
    parser.add_argument("--dry-run", action="store_true", help="Fetch and extract, but do not upload or save state")
    args = parser.parse_args()

    load_env(args.env_file)
    token = os.environ.get("X_BEARER_TOKEN")
    if not token:
        raise SystemExit("X_BEARER_TOKEN is not configured")

    endpoint = os.environ.get("COLLECTOR_ENDPOINT", "").rstrip("/")
    collector_key = os.environ.get("COLLECTOR_API_KEY", "")
    if not args.dry_run and (not endpoint or not collector_key):
        raise SystemExit("COLLECTOR_ENDPOINT and COLLECTOR_API_KEY are required unless --dry-run is used")

    state = read_state(args.state_file)
    payload = search_posts(token, args.query, state, args.bootstrap_hours)
    users = {user["id"]: user for user in payload.get("includes", {}).get("users", [])}
    posts = payload.get("data", [])
    accepted = 0

    for post in reversed(posts):
        username = users.get(post.get("author_id"), {}).get("username")
        post_id = post["id"]
        text = (post.get("note_tweet") or {}).get("text", post.get("text", ""))
        published_at = datetime.fromisoformat(post["created_at"].replace("Z", "+00:00"))
        result = extract_event(text, published_at, post_id)
        source_url = f"https://x.com/{username}/status/{post_id}" if username else f"https://x.com/i/status/{post_id}"
        candidate = {
            "event_fingerprint": result["event_fingerprint"],
            "confidence": result["confidence"],
            "extracted": result["extracted"],
            "source": {
                "type": "x",
                "key": post_id,
                "url": source_url,
                "name": "X",
                "author_handle": username,
                "content_hash": result["content_hash"],
            },
        }

        # Very weak matches remain outside the database until extraction improves.
        if result["confidence"] < 0.30:
            print(f"skip {post_id}: confidence={result['confidence']:.3f}")
            continue

        if not args.dry_run:
            post_candidate(f"{endpoint}/api/internal/candidates", collector_key, candidate)
        print(json.dumps({
            "post_id": post_id,
            "confidence": result["confidence"],
            "title": result["extracted"]["title"],
            "venue": result["extracted"]["venue"],
            "start_date": result["extracted"]["start_date"],
            "end_date": result["extracted"]["end_date"],
        }, ensure_ascii=False))
        accepted += 1

    if not args.dry_run and payload.get("meta", {}).get("newest_id"):
        write_state(args.state_file, {
            "newest_id": payload["meta"]["newest_id"],
            "updated_at": datetime.now(timezone.utc).isoformat(),
        })

    print(f"collected={len(posts)} accepted={accepted}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

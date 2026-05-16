#!/usr/bin/env python3
"""대상 transcript를 로컬 큐로 덤프 (DB read 1회, 페이지네이션).

사용법: source .env.local && python3 scripts/dump_pending.py [--days 30]
출력:
  /tmp/backfill_queue/<vid>.txt   — transcript 본문
  /tmp/backfill_queue/_meta.json  — [{vid, channel_slug, title, published_at}, ...]
"""
import json
import os
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timedelta, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scripts.channel_config import STOCK_ECON_SLUGS

QUEUE = "/tmp/backfill_queue"
DAYS = 30
PAGE = 50  # transcript 본문 포함이라 작게


def _env(k: str) -> str:
    v = os.environ.get(k)
    if v:
        return v
    for p in [".env.local", os.path.expanduser("~/.claude/.env")]:
        if os.path.isfile(p):
            with open(p, encoding="utf-8") as f:
                for line in f:
                    if line.startswith(f"{k}="):
                        return line.split("=", 1)[1].strip().strip('"').strip("'")
    return ""


def _get(url: str, key: str, rng: str) -> list:
    req = urllib.request.Request(
        url,
        headers={
            "apikey": key,
            "Authorization": f"Bearer {key}",
            "Range": rng,
            "Range-Unit": "items",
            # Cloudflare 1010 우회
            "User-Agent": "curl/8.7.1",
        },
    )
    for attempt in range(6):  # Status=Checking / 과부하 중 재시도
        try:
            with urllib.request.urlopen(req, timeout=30) as r:
                return json.loads(r.read())
        except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError):
            if attempt == 5:
                raise
            time.sleep(10 * (attempt + 1))  # 백오프
    return []


def main() -> int:
    days = DAYS
    if "--days" in sys.argv:
        days = int(sys.argv[sys.argv.index("--days") + 1])

    url = _env("NEXT_PUBLIC_SUPABASE_URL") or _env("SUPABASE_URL")
    key = _env("SUPABASE_SERVICE_ROLE_KEY") or _env("SUPABASE_SERVICE_KEY")
    if not url or not key:
        print(json.dumps({"error": "SUPABASE url/key 미설정"}))
        return 1

    os.makedirs(QUEUE, exist_ok=True)
    cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).strftime("%Y-%m-%d")
    slugs = ",".join(STOCK_ECON_SLUGS)
    base = (
        f"{url}/rest/v1/transcripts"
        f"?select=vid,channel_slug,title,published_at,transcript,summary"
        f"&channel_slug=in.({slugs})&transcript=not.is.null"
        f"&published_at=gte.{cutoff}&order=published_at.desc"
    )

    meta: list = []
    off = 0
    dumped = 0
    skipped = 0
    while True:
        rows = _get(base, key, f"{off}-{off + PAGE - 1}")
        if not rows:
            break
        for r in rows:
            s = r.get("summary")
            if s and "macro_views" in s:  # 이미 v2 → skip
                skipped += 1
                continue
            vid = r["vid"]
            with open(f"{QUEUE}/{vid}.txt", "w", encoding="utf-8") as f:
                f.write(r.get("transcript") or "")
            meta.append(
                {
                    "vid": vid,
                    "channel_slug": r["channel_slug"],
                    "title": r["title"],
                    "published_at": r.get("published_at"),
                }
            )
            dumped += 1
        if len(rows) < PAGE:
            break
        off += PAGE
        time.sleep(1)  # 페이지 간 텀

    with open(f"{QUEUE}/_meta.json", "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)

    print(
        json.dumps(
            {
                "dumped": dumped,
                "skipped_v2": skipped,
                "queue": QUEUE,
                "meta": f"{QUEUE}/_meta.json",
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())

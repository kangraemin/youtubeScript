#!/usr/bin/env python3
"""transcripts.duration_sec NULL인 영상을 YouTube API로 채운다.

웹 쇼츠 필터(길이 기준)를 위해 영상 길이가 필요하다. 크롤러는 duration을 조회하지만
쇼츠 제외 판정에만 쓰고 저장하지 않아 기존 행은 전부 NULL이다.

videos.list는 한 번에 50개 id를 받고 1 unit만 소모하므로 quota 부담이 거의 없다.
삭제·비공개된 영상은 응답에 빠지는데, 재조회를 반복하지 않도록 -1로 마킹한다.

Usage:
    source .env.local && python scripts/backfill_duration.py
    python scripts/backfill_duration.py --limit 500
"""
import argparse
import os
import re
import sys
import time
import json
import urllib.parse
import urllib.request
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv

from worker.supabase_client import get_client, call_with_retry

_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(_ROOT / ".env.local")

BATCH = 50
UNKNOWN = -1  # 삭제·비공개로 조회 불가 — 재시도 방지 마킹


def iso_to_sec(iso: str) -> int:
    m = re.match(r"PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?", iso or "")
    if not m:
        return 0
    h, mi, s = [int(x or 0) for x in m.groups()]
    return h * 3600 + mi * 60 + s


def fetch_durations(ids: list[str], key: str) -> dict[str, int]:
    q = urllib.parse.urlencode({"part": "contentDetails", "id": ",".join(ids), "key": key})
    with urllib.request.urlopen(
        "https://www.googleapis.com/youtube/v3/videos?" + q, timeout=30
    ) as r:
        d = json.loads(r.read().decode())
    return {
        it["id"]: iso_to_sec(it["contentDetails"]["duration"]) for it in d.get("items", [])
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=0, help="처리할 최대 건수 (0=전체)")
    args = ap.parse_args()

    key = os.environ.get("YOUTUBE_API_KEY")
    if not key:
        print("YOUTUBE_API_KEY 없음", file=sys.stderr)
        return 1

    db = get_client()
    done = 0
    missing = 0

    while True:
        rows = call_with_retry(
            lambda: db.table("transcripts")
            .select("vid")
            .is_("duration_sec", "null")
            .limit(BATCH)
            .execute()
        ).data
        if not rows:
            break

        ids = [r["vid"] for r in rows]
        got = fetch_durations(ids, key)

        for vid in ids:
            sec = got.get(vid, UNKNOWN)
            if sec == UNKNOWN:
                missing += 1
            call_with_retry(
                lambda v=vid, s=sec: db.table("transcripts")
                .update({"duration_sec": s})
                .eq("vid", v)
                .execute()
            )

        done += len(ids)
        print(f"  {done}건 처리 (조회불가 {missing})", flush=True)

        if args.limit and done >= args.limit:
            break
        time.sleep(0.2)

    print(f"\n완료: {done}건 (조회불가 {missing}건은 {UNKNOWN}로 마킹)")
    return 0


if __name__ == "__main__":
    sys.exit(main())

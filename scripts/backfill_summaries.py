#!/usr/bin/env python3
"""7개 주식·경제 채널 × 최근 30일 미요약 후보 카운트.

/loop을 켜기 전 얼마나 작업이 남아있는지 확인용.
"""
import json
import os
import sys
from datetime import datetime, timedelta, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from worker.supabase_client import get_client
from scripts.channel_config import STOCK_ECON_SLUGS


def main() -> int:
    cutoff = (datetime.now(timezone.utc) - timedelta(days=30)).date().isoformat()
    db = get_client()
    r = (
        db.table("transcripts")
        .select("vid,channel_slug,title,published_at")
        .in_("channel_slug", STOCK_ECON_SLUGS)
        .gte("published_at", cutoff)
        .is_("summary", "null")
        .not_.is_("transcript", "null")
        .order("published_at", desc=True)
        .execute()
    )
    rows = r.data or []
    by_ch: dict[str, list[str]] = {}
    for x in rows:
        by_ch.setdefault(x["channel_slug"], []).append(x["vid"])

    print(json.dumps({
        "cutoff": cutoff,
        "total": len(rows),
        "by_channel": {k: len(v) for k, v in by_ch.items()},
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
"""DB에서 has_transcript=false인 영상들을 Playwright로 수집해 rawdata 저장 + has_transcript=true 세팅.

transcript 본문은 로컬 rawdata가 단일 소스 — DB엔 본문을 쓰지 않는다(메타만).

Usage:
    python scripts/backfill_from_db.py
    python scripts/backfill_from_db.py --headless
    python scripts/backfill_from_db.py --channel sampro_tv
"""
import argparse
import json
import os
import sys
import time
from datetime import datetime
from pathlib import Path

from playwright.sync_api import sync_playwright
from dotenv import load_dotenv

_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(_ROOT / ".env.local")
os.environ.setdefault("SUPABASE_URL", os.environ.get("NEXT_PUBLIC_SUPABASE_URL", ""))
os.environ.setdefault("SUPABASE_SERVICE_KEY", os.environ.get("SUPABASE_SERVICE_ROLE_KEY", ""))
sys.path.insert(0, str(_ROOT / "worker"))
sys.path.insert(0, str(_ROOT / "scripts"))
from supabase_client import get_client, call_with_retry
from crawl_youtube_transcripts import get_transcript, save_transcript


def fmt_segments(segments: list) -> str:
    lines = []
    for s in segments:
        m, sec = divmod(int(s["timestamp"].split(":")[0]) * 60 + int(s["timestamp"].split(":")[1]) if ":" in s["timestamp"] else int(float(s.get("start", 0))), 60)
        lines.append(f"{m}:{sec:02d} {s['text']}")
    return "\n".join(lines)


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--headless", action="store_true")
    p.add_argument("--channel", default="all")
    args = p.parse_args()

    db = get_client()

    # DB에서 NULL 목록 가져오기
    rows = []
    page = 0
    while True:
        q = db.table("transcripts").select("vid, channel, channel_slug, title, url, published_at").eq("has_transcript", False)
        if args.channel != "all":
            q = q.eq("channel_slug", args.channel)
        r = call_with_retry(lambda: q.range(page * 1000, (page + 1) * 1000 - 1).execute())
        rows.extend(r.data)
        if len(r.data) < 1000:
            break
        page += 1

    if not rows:
        print("NULL 없음")
        return

    print(f"총 {len(rows)}개 has_transcript=false 처리 시작")
    from collections import Counter
    for ch, n in Counter(r["channel_slug"] for r in rows).most_common():
        print(f"  {ch}: {n}")

    ok = fail = 0

    with sync_playwright() as pw:
        browser = pw.chromium.launch(
            headless=args.headless,
            args=["--disable-blink-features=AutomationControlled"],
        )
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            viewport={"width": 1280, "height": 800},
        )
        page_obj = context.new_page()

        TRANSCRIPTS_DIR = _ROOT / "rawdata" / "transcripts"
        BATCH = []

        for i, row in enumerate(rows, 1):
            vid = row["vid"]
            slug = row["channel_slug"]

            segments = get_transcript(page_obj, vid)
            if segments:
                # txt 파일을 rawdata에 저장 (transcript 본문 단일 소스)
                save_transcript(str(TRANSCRIPTS_DIR), slug, vid,
                                row.get("title", ""), row.get("url", ""), segments)
                txt_file = TRANSCRIPTS_DIR / slug / f"{vid}.txt"
                if txt_file.exists() and txt_file.stat().st_size > 0:
                    BATCH.append(vid)   # DB엔 본문 안 씀 — has_transcript=true 세팅 대상 vid만
                ok += 1
            else:
                fail += 1

            # 50개마다 has_transcript 일괄 세팅 (메타만, 본문 미기록)
            if len(BATCH) >= 50:
                try:
                    call_with_retry(lambda: db.table("transcripts").update({"has_transcript": True}).in_("vid", BATCH).execute())
                except Exception as e:
                    print(f"  update 에러: {e}")
                print(f"  [{i}/{len(rows)}] ok={ok} fail={fail} — has_transcript {len(BATCH)}개 세팅", flush=True)
                BATCH.clear()

        # 나머지 세팅
        if BATCH:
            try:
                call_with_retry(lambda: db.table("transcripts").update({"has_transcript": True}).in_("vid", BATCH).execute())
            except Exception as e:
                print(f"  update 에러: {e}")
            print(f"  최종 has_transcript {len(BATCH)}개 세팅", flush=True)

        context.close()
        browser.close()

    print(f"\n완료: ok={ok} fail={fail}")


if __name__ == "__main__":
    main()

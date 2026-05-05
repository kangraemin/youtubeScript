#!/usr/bin/env python3
"""Playwright로 누락된 transcript .txt 파일을 채운다.
기존 crawl_youtube_transcripts.py의 get_transcript 함수 재사용.

Usage:
    python scripts/backfill_transcripts.py
    python scripts/backfill_transcripts.py --channel sampro_tv
    python scripts/backfill_transcripts.py --headless
"""
import argparse
import json
import os
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

# 기존 crawler에서 재사용
_HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(_HERE))
from crawl_youtube_transcripts import get_transcript, save_transcript

TRANSCRIPTS_DIR = _HERE.parent / "rawdata" / "transcripts"


def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument("--channel", default="all")
    p.add_argument("--headless", action="store_true")
    return p.parse_args()


def main():
    args = parse_args()

    ch_dirs = (
        sorted(TRANSCRIPTS_DIR.iterdir())
        if args.channel == "all"
        else [TRANSCRIPTS_DIR / args.channel]
    )

    # 누락 목록 수집
    tasks = []  # (ch_dir, vid_info)
    for ch_dir in ch_dirs:
        if not ch_dir.is_dir():
            continue
        list_file = ch_dir / "_list.json"
        if not list_file.exists():
            continue
        videos = json.load(open(list_file))
        missing = [v for v in videos if not (ch_dir / f"{v['vid']}.txt").exists()]
        for v in missing:
            tasks.append((ch_dir, v))

    if not tasks:
        print("누락 없음")
        return

    print(f"총 {len(tasks)}개 누락 처리 시작")

    with sync_playwright() as pw:
        browser = pw.chromium.launch(
            headless=args.headless,
            args=["--disable-blink-features=AutomationControlled"],
        )
        context = browser.new_context(
            user_agent=(
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0.0.0 Safari/537.36"
            ),
            viewport={"width": 1280, "height": 800},
        )
        page = context.new_page()

        ok = fail = 0
        current_ch = None

        for i, (ch_dir, v) in enumerate(tasks, 1):
            if ch_dir.name != current_ch:
                current_ch = ch_dir.name
                missing_count = sum(1 for c, _ in tasks if c.name == current_ch)
                print(f"\n[{current_ch}] {missing_count}개 누락", flush=True)

            segments = get_transcript(page, v["vid"])
            if segments:
                save_transcript(
                    str(TRANSCRIPTS_DIR), ch_dir.name,
                    v["vid"], v.get("title", ""), v.get("url", ""),
                    segments,
                )
                ok += 1
            else:
                fail += 1

            if i % 20 == 0:
                print(f"  진행 {i}/{len(tasks)} ok={ok} fail={fail}", flush=True)

        context.close()
        browser.close()

    print(f"\n완료: ok={ok} fail={fail}")


if __name__ == "__main__":
    main()

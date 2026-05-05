#!/usr/bin/env python3
"""
YouTube transcript fetcher (no browser).
Usage:
    python scripts/get_transcript.py https://www.youtube.com/watch?v=VIDEO_ID
    python scripts/get_transcript.py VIDEO_ID
    python scripts/get_transcript.py --channel moneycomics
"""
import argparse
import json
import re
import sys
from pathlib import Path

from youtube_transcript_api import YouTubeTranscriptApi, NoTranscriptFound, TranscriptsDisabled

CHANNELS = [
    {"id": "UCehQiKylaW68H_OtRS36wGQ", "slug": "dulcinea_studio", "name": "둘시네아"},
    {"id": "UCfpaSruWW3S4dibonKXENjA", "slug": "tzuyang",          "name": "쯔양"},
    {"id": "UCzgpOnor-MzT-1iflZil2GQ", "slug": "jaesunrang",       "name": "재선랑"},
    {"id": "UC-OAmhcFgX9t_OF6fQ-4B1w", "slug": "kimjjamppong",     "name": "김쨈뽕"},
    {"id": "UC-x55HF1-IilhxZOzwJm7JA", "slug": "kimsawon",         "name": "김사원"},
    {"id": "UCJo6G1u0e_-wS-JQn3T-zEw", "slug": "moneycomics",      "name": "머니코믹스"},
]


def extract_video_id(url_or_id: str) -> str:
    m = re.search(r"[?&]v=([\w-]{11})", url_or_id)
    return m.group(1) if m else url_or_id.strip()


def fmt_time(seconds: float) -> str:
    s = int(seconds)
    return f"{s // 60}:{s % 60:02d}"


_api = YouTubeTranscriptApi()


def fetch_transcript(vid: str) -> list | None:
    try:
        return list(_api.fetch(vid, languages=["ko", "a.ko", "ko-KR", "en", "a.en"]))
    except (NoTranscriptFound, TranscriptsDisabled):
        return None


def print_transcript(segs: list):
    for s in segs:
        print(f"{fmt_time(s.start)} {s.text}")


def main():
    p = argparse.ArgumentParser(description="YouTube transcript fetcher (no browser)")
    p.add_argument("url", nargs="?", help="YouTube URL or video ID")
    p.add_argument("--channel", help="Channel slug — uses rawdata/transcripts/<slug>/_list.json")
    p.add_argument("--output-dir", default="rawdata/transcripts")
    args = p.parse_args()

    if args.url:
        vid = extract_video_id(args.url)
        segs = fetch_transcript(vid)
        if segs:
            print_transcript(segs)
        else:
            print(f"❌ 자막 없음: {vid}", file=sys.stderr)
            sys.exit(1)

    elif args.channel:
        ch = next((c for c in CHANNELS if c["slug"] == args.channel), None)
        if not ch:
            print(f"❌ 알 수 없는 채널: {args.channel}", file=sys.stderr)
            sys.exit(1)
        list_path = Path(args.output_dir) / args.channel / "_list.json"
        if not list_path.exists():
            print(f"❌ _list.json 없음 — 먼저 crawl_youtube_transcripts.py 실행 필요", file=sys.stderr)
            sys.exit(1)
        videos = json.loads(list_path.read_text())
        for v in videos:
            print(f"\n=== {v['title']} ({v['vid']}) ===")
            segs = fetch_transcript(v["vid"])
            if segs:
                print_transcript(segs)
            else:
                print("  ❌ 자막 없음")
    else:
        p.print_help()


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""youtube-transcript-api로 누락된 transcript .txt 파일을 채운다.

Usage:
    python scripts/backfill_transcripts.py
    python scripts/backfill_transcripts.py --channel sampro_tv
    python scripts/backfill_transcripts.py --dry-run
"""
import argparse
import json
import os
import time
from datetime import datetime
from pathlib import Path

from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api._errors import NoTranscriptFound, TranscriptsDisabled, VideoUnavailable

TRANSCRIPTS_DIR = Path(__file__).resolve().parent.parent / "rawdata" / "transcripts"


def fmt_timestamp(seconds: float) -> str:
    s = int(seconds)
    m, s = divmod(s, 60)
    return f"{m}:{s:02d}"


def fetch_transcript(api, vid: str) -> list[dict] | None:
    try:
        tl = api.list(vid)
        # prefer manual ko, then auto ko, then any
        for lang in ['ko', 'ko-KR']:
            try:
                t = api.fetch(vid, languages=[lang])
                return list(t)
            except Exception:
                pass
        # fallback: first available
        t = api.fetch(vid)
        return list(t)
    except (TranscriptsDisabled, VideoUnavailable, NoTranscriptFound):
        return None
    except Exception as e:
        print(f"    [warn] {vid}: {e}")
        return None


def save_txt(ch_dir: Path, vid: str, v: dict, segments: list) -> None:
    title = v.get("title", "")
    url = v.get("url", f"https://www.youtube.com/watch?v={vid}")
    collected_at = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
    lines = [title, url, f"video_id: {vid}", f"collected_at: {collected_at}", ""]
    for seg in segments:
        ts = fmt_timestamp(seg.start)
        text = seg.text.replace("\n", " ").strip()
        if text:
            lines.append(f"{ts} {text}")
    (ch_dir / f"{vid}.txt").write_text("\n".join(lines), encoding="utf-8")


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--channel", default="all")
    p.add_argument("--dry-run", action="store_true")
    args = p.parse_args()

    api = YouTubeTranscriptApi()

    dirs = sorted(TRANSCRIPTS_DIR.iterdir()) if args.channel == "all" else [TRANSCRIPTS_DIR / args.channel]

    grand_ok = grand_fail = grand_skip = 0

    for ch_dir in dirs:
        if not ch_dir.is_dir():
            continue
        list_file = ch_dir / "_list.json"
        if not list_file.exists():
            continue

        with open(list_file) as f:
            videos = json.load(f)

        missing = [v for v in videos if not (ch_dir / f"{v['vid']}.txt").exists()]
        if not missing:
            continue

        print(f"\n[{ch_dir.name}] {len(missing)} 개 누락")
        ok = fail = 0

        for i, v in enumerate(missing):
            vid = v["vid"]
            if args.dry_run:
                print(f"  dry: {vid}")
                continue

            segs = fetch_transcript(api, vid)
            if segs:
                save_txt(ch_dir, vid, v, segs)
                ok += 1
                if (i + 1) % 10 == 0:
                    print(f"  [{ch_dir.name}] {i+1}/{len(missing)} ok={ok} fail={fail}", flush=True)
            else:
                fail += 1
            time.sleep(0.3)

        print(f"  [{ch_dir.name}] 완료: ok={ok} fail={fail}")
        grand_ok += ok
        grand_fail += fail
        grand_skip += len(videos) - len(missing)

    print(f"\n전체: ok={grand_ok} fail={grand_fail}")


if __name__ == "__main__":
    main()

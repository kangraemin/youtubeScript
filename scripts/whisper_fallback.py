#!/usr/bin/env python3
"""자막이 끝내 안 받아지는 먹방 영상을 오디오로 받아 맥 로컬 Whisper로 받아 적는다.

대상: 먹방 채널 <slug>/_failed.json 중 크롤러가 GIVEUP_FAILS번 실패해 포기한 영상(아직 txt 없음).
yt-dlp로 오디오만 내려받고(브라우저 쿠키 사용), mlx-whisper large-v3-turbo로 받아 적은 뒤
크롤러와 같은 형식(헤더 4줄 + 빈 줄 + "M:SS text")으로 <slug>/<vid>.txt에 쓴다. 오디오는 바로 지운다.

Usage:
    python scripts/whisper_fallback.py --max-videos 5
    python scripts/whisper_fallback.py --vid QWY3eNslYn0 --slug chureupkyeon --force
"""
import argparse
import random
import subprocess
import sys
import tempfile
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scripts.channel_config import FOOD_SLUGS  # noqa: E402
from scripts.crawl_youtube_transcripts import (  # noqa: E402
    GIVEUP_FAILS, _fmt_ts, load_failed, save_failed, save_transcript,
)

YT_DLP = "/opt/homebrew/bin/yt-dlp"
MODEL = "mlx-community/whisper-large-v3-turbo"


def candidates(out_dir: str) -> list[dict]:
    out = []
    for slug in FOOD_SLUGS:
        for vid, f in load_failed(out_dir, slug).items():
            if f.get("count", 0) < GIVEUP_FAILS or f.get("whisper_failed"):
                continue
            if (Path(out_dir) / slug / f"{vid}.txt").exists():
                continue
            out.append({"slug": slug, "vid": vid, "title": f.get("title", ""), "url": f.get("url", "")})
    return out


def transcribe(vid: str, slug: str, title: str, url: str, out_dir: str) -> bool:
    import mlx_whisper

    url = url or f"https://www.youtube.com/watch?v={vid}"
    with tempfile.TemporaryDirectory() as tmp:
        audio = Path(tmp) / f"{vid}.m4a"
        # 쿠키 없이 먼저 받는다. --cookies-from-browser chrome은 키체인 확인 창을 기다리며 15분 넘게 멈췄다(2026-10-19 실측).
        # 연령 제한 등으로 실패할 때만 쿠키를 붙여 짧게 한 번 더 시도한다.
        err = ""
        for extra, limit in (([], 600), (["--cookies-from-browser", "chrome"], 120)):
            try:
                r = subprocess.run(
                    [YT_DLP, "-x", "--audio-format", "m4a", *extra,
                     "--no-playlist", "-q", "-o", str(audio), url],
                    capture_output=True, text=True, timeout=limit,
                )
                err = r.stderr.strip()[-200:]
            except subprocess.TimeoutExpired:
                err = f"timeout {limit}s"
            if audio.exists():
                break
        if not audio.exists():
            print(f"  [whisper] 오디오 받기 실패 {vid}: {err}", flush=True)
            return False
        res = mlx_whisper.transcribe(str(audio), path_or_hf_repo=MODEL, language="ko")
    segs = [{"timestamp": _fmt_ts(s["start"]), "text": s["text"].strip()}
            for s in res.get("segments", []) if s.get("text", "").strip()]
    if not segs:
        return False
    if not title:
        title = vid
    save_transcript(out_dir, slug, vid, title, url, segs)
    print(f"  [whisper] {slug}/{vid}: {len(segs)} segments", flush=True)
    return True


def main():
    p = argparse.ArgumentParser(description="자막 없는 먹방 영상 → yt-dlp 오디오 + mlx-whisper")
    p.add_argument("--max-videos", type=int, default=5)
    p.add_argument("--output-dir", default="rawdata/transcripts")
    p.add_argument("--vid", help="이 영상 하나만 처리")
    p.add_argument("--slug", help="--vid와 함께 쓰는 채널 slug")
    p.add_argument("--force", action="store_true", help="txt가 있어도 다시 받아 적는다(--vid 전용)")
    args = p.parse_args()

    if args.vid:
        if not args.slug:
            p.error("--vid에는 --slug가 필요하다")
        path = Path(args.output_dir) / args.slug / f"{args.vid}.txt"
        if path.exists() and not args.force:
            print(f"이미 있음: {path}")
            return
        ok = transcribe(args.vid, args.slug, "", "", args.output_dir)
        sys.exit(0 if ok else 1)

    todo = candidates(args.output_dir)[: args.max_videos]
    print(f"whisper 대상 {len(todo)}개", flush=True)
    for i, c in enumerate(todo):
        if i:
            time.sleep(random.uniform(20, 40))  # 오디오 다운로드 간격 — 연속 요청으로 막히지 않게
        ok = transcribe(c["vid"], c["slug"], c["title"], c["url"], args.output_dir)
        failed = load_failed(args.output_dir, c["slug"])
        if ok:
            failed.pop(c["vid"], None)
        elif c["vid"] in failed:
            failed[c["vid"]]["whisper_failed"] = True  # 다시 시도하지 않는다(삭제·연령제한 영상 등)
        save_failed(args.output_dir, c["slug"], failed)


if __name__ == "__main__":
    main()

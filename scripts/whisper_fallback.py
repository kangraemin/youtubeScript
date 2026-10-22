#!/usr/bin/env python3
"""자막이 끝내 안 받아지는 먹방 영상을 오디오로 받아 맥 로컬 Whisper로 받아 적는다.

대상: 먹방 채널 <slug>/_failed.json 중 크롤러가 GIVEUP_FAILS번 실패해 포기한 영상(아직 txt 없음).
yt-dlp로 오디오만 내려받고(브라우저 쿠키 사용), mlx-whisper large-v3-turbo로 받아 적은 뒤
크롤러와 같은 형식(헤더 4줄 + 빈 줄 + "M:SS text")으로 <slug>/<vid>.txt에 쓴다. 오디오는 바로 지운다.

Usage:
    python scripts/whisper_fallback.py --max-videos 5
    python scripts/whisper_fallback.py --all-missing --shard 0/3   # 자막이 IP 차단으로 안 받아질 때 남은 먹방 영상 전체(3개 프로세스로 나눠 받기)
    python scripts/whisper_fallback.py --vid QWY3eNslYn0 --slug chureupkyeon --force
"""
import argparse
import random
import re
import subprocess
import sys
import tempfile
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scripts.channel_config import FOOD_SLUGS, food_channels, is_compilation  # noqa: E402
from scripts.crawl_youtube_transcripts import (  # noqa: E402
    GIVEUP_FAILS, _fmt_ts, load_failed, save_failed, save_transcript,
)

YT_DLP = "/opt/homebrew/bin/yt-dlp"
MODEL = "mlx-community/whisper-large-v3-turbo"
FFMPEG = "/opt/homebrew/bin/ffmpeg"
# 2배속 + 이전 문맥 끔: 15분 영상 452초 → 47초, 같은 말 되풀이 110줄 → 27줄(2026-10-22 실측). 1.5배속은 외국 글자가 섞여 더 나빴다.
SPEED = 2.0
FOREIGN = re.compile(r"[\u0400-\u04FF\u0600-\u06FF\u0E00-\u0E7F\uFFFD]")  # 키릴·아랍·태국 글자, 깨진 글자


def clean_segments(segs: list[dict], speed: float) -> list[dict]:
    """빠르게 돌린 시각을 원래 시각으로 되돌리고, 빈 줄·바로 앞과 같은 말·외국 글자가 섞인 줄을 버린다."""
    out, prev = [], None
    for s in segs:
        text = s.get("text", "").strip()
        if not text or text == prev or FOREIGN.search(text):
            continue
        out.append({"timestamp": _fmt_ts(s["start"] * speed), "text": text})
        prev = text
    return out


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


def all_missing(out_dir: str, channels: list[str] | None = None) -> list[dict]:
    """먹방 채널 6년치 영상 중 txt가 없는 것 전부(모아보기·2시간 초과·whisper 실패 제외). 목록은 Data API라 IP 차단과 무관하다."""
    from googleapiclient.discovery import build
    from scripts.crawl_youtube_transcripts import _load_env_key, get_channel_videos_api
    import os
    yt = build("youtube", "v3", developerKey=os.environ.get("YOUTUBE_API_KEY") or _load_env_key(".env.local", "YOUTUBE_API_KEY"))
    out = []
    for ch in food_channels():
        if channels and ch["slug"] not in channels:
            continue
        failed = load_failed(out_dir, ch["slug"])
        for v in get_channel_videos_api(yt, ch, 0, 2190):
            if (Path(out_dir) / ch["slug"] / f"{v['vid']}.txt").exists() or failed.get(v["vid"], {}).get("whisper_failed"):
                continue
            if is_compilation(v.get("title", ""), v.get("duration_sec", 0)):
                continue
            out.append({"slug": ch["slug"], "vid": v["vid"], "title": v.get("title", ""), "url": v.get("url", "")})
    return out


def shard(items: list[dict], spec: str) -> list[dict]:
    """'i/n' → vid 해시로 n등분한 것 중 i번째. 프로세스마다 겹치지 않게 나눈다."""
    import zlib
    i, n = (int(x) for x in spec.split("/"))
    return [c for c in items if zlib.crc32(c["vid"].encode()) % n == i]


def transcribe(vid: str, slug: str, title: str, url: str, out_dir: str) -> bool:
    import mlx_whisper

    url = url or f"https://www.youtube.com/watch?v={vid}"
    with tempfile.TemporaryDirectory() as tmp:
        audio = Path(tmp) / "a"
        # 쿠키 없이 먼저 받는다. --cookies-from-browser chrome은 키체인 확인 창을 기다리며 15분 넘게 멈췄다(2026-10-19 실측).
        # 연령 제한 등으로 실패할 때만 쿠키를 붙여 짧게 한 번 더 시도한다.
        err = ""
        for extra, limit in (([], 600), (["--cookies-from-browser", "chrome"], 120)):
            try:
                r = subprocess.run(
                    # m4a로 다시 바꾸지 않는다: 변환만 6분 걸렸다. whisper는 webm을 그대로 읽는다
                    [YT_DLP, "-f", "bestaudio", *extra,
                     "--no-playlist", "-q", "-o", f"{audio}.%(ext)s", url],
                    capture_output=True, text=True, timeout=limit,
                )
                err = r.stderr.strip()[-200:]
            except subprocess.TimeoutExpired:
                err = f"timeout {limit}s"
            got = sorted(Path(tmp).glob("a.*"))
            if got:
                break
        if not got:
            print(f"  [whisper] 오디오 받기 실패 {vid}: {err}", flush=True)
            return False
        fast = Path(tmp) / "fast.webm"
        r = subprocess.run([FFMPEG, "-y", "-v", "error", "-i", str(got[0]), "-filter:a", f"atempo={SPEED}",
                            "-c:a", "libopus", str(fast)], capture_output=True, text=True, timeout=300)
        if r.returncode:
            print(f"  [whisper] 배속 변환 실패 {vid}: {r.stderr.strip()[-200:]}", flush=True)
            return False
        res = mlx_whisper.transcribe(str(fast), path_or_hf_repo=MODEL, language="ko",
                                     condition_on_previous_text=False)
    segs = clean_segments(res.get("segments", []), SPEED)
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
    p.add_argument("--all-missing", action="store_true", help="실패 기록과 상관없이 txt 없는 먹방 영상 전부")
    p.add_argument("--channel", help="--all-missing 대상 slug(쉼표 구분)")
    p.add_argument("--shard", default="0/1", help="i/n — n개 프로세스로 나눠 돌릴 때 이 프로세스 몫")
    p.add_argument("--gap", type=float, default=30, help="오디오 다운로드 사이 평균 대기 초")
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

    if args.all_missing:
        todo = shard(all_missing(args.output_dir, args.channel.split(",") if args.channel else None), args.shard)
    else:
        todo = candidates(args.output_dir)
    todo = todo[: args.max_videos] if args.max_videos > 0 else todo
    print(f"whisper 대상 {len(todo)}개 (shard {args.shard})", flush=True)
    done = 0
    for i, c in enumerate(todo):
        if i:
            time.sleep(random.uniform(args.gap * 0.5, args.gap * 1.5))  # 오디오 다운로드 간격 — 연속 요청으로 막히지 않게
        if (Path(args.output_dir) / c["slug"] / f"{c['vid']}.txt").exists():  # 그 사이 크롤러가 받았다
            continue
        ok = transcribe(c["vid"], c["slug"], c["title"], c["url"], args.output_dir)
        done += ok
        failed = load_failed(args.output_dir, c["slug"])
        if ok:
            failed.pop(c["vid"], None)
        else:
            # 다시 시도하지 않는다(삭제·연령제한 영상 등)
            failed.setdefault(c["vid"], {"count": 0, "title": c["title"], "url": c["url"]})["whisper_failed"] = True
        save_failed(args.output_dir, c["slug"], failed)
        if (i + 1) % 10 == 0:
            print(f"[whisper {args.shard}] 진행 {i + 1}/{len(todo)} ok={done}", flush=True)
    print(f"[whisper {args.shard}] 끝 ok={done}/{len(todo)}", flush=True)


if __name__ == "__main__":
    main()

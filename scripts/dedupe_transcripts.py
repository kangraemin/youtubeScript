#!/usr/bin/env python3
"""기존 DB transcripts 중복(2배 dump) 정리. 기본 dry-run, --apply 로 실제 반영.
손실 없음: 타임스탬프 역행(중복 사이클 시작) 이후만 절단, 역행 없으면 무변경."""
import argparse
import os
import re
import sys
from pathlib import Path

from dotenv import load_dotenv

_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(_ROOT / ".env.local")
os.environ.setdefault("SUPABASE_URL", os.environ.get("NEXT_PUBLIC_SUPABASE_URL", ""))
os.environ.setdefault("SUPABASE_SERVICE_KEY", os.environ.get("SUPABASE_SERVICE_ROLE_KEY", ""))
sys.path.insert(0, str(_ROOT / "worker"))
sys.path.insert(0, str(_ROOT))
from supabase_client import get_client
from scripts.crawl_youtube_transcripts import _ts_to_seconds

TS_RE = re.compile(r"^(\d{1,2}:\d{2}(?::\d{2})?)\s")


def dedup_text(text: str) -> tuple[str, bool]:
    """(새 텍스트, 변경여부). 중복(타임스탬프 역행) 없으면 (원본, False)."""
    if not text:
        return text, False
    lines = text.split("\n")
    first = next((i for i, l in enumerate(lines) if TS_RE.match(l)), None)
    if first is None:
        return text, False
    header, segs = lines[:first], lines[first:]
    prev, cut = -1, None
    for i, ln in enumerate(segs):
        m = TS_RE.match(ln)
        if not m:                       # 이전 세그먼트 본문 연장 라인
            continue
        sec = _ts_to_seconds(m.group(1))
        if sec is None:
            continue
        if sec < prev:
            cut = i
            break
        prev = sec
    if cut is None:
        return text, False
    return "\n".join(header + segs[:cut]).rstrip(), True


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true", help="실제 DB 반영 (기본 dry-run)")
    ap.add_argument("--limit", type=int, default=0, help="검사 행 수 제한 (테스트용)")
    args = ap.parse_args()

    db = get_client()
    # transcript 컬럼이 거대해 페이지당 payload가 무거우므로 작은 페이지 + vid 정렬로
    # 안정적 keyset 페이지네이션(offset range는 order 없으면 미정의·timeout 위험)
    size, dup, fixed, scanned = 150, 0, 0, 0
    cursor = ""
    while True:
        q = (db.table("transcripts").select("vid,transcript")
             .not_.is_("transcript", "null")
             .gt("vid", cursor).order("vid").limit(size).execute())
        rows = q.data or []
        if not rows:
            break
        for r in rows:
            scanned += 1
            new, changed = dedup_text(r["transcript"])
            if not changed:
                continue
            dup += 1
            old_len, new_len = len(r["transcript"]), len(new)
            print(f"  DUP {r['vid']}: {old_len}→{new_len} chars")
            if args.apply:
                db.table("transcripts").update({"transcript": new}).eq("vid", r["vid"]).execute()
                fixed += 1
        cursor = rows[-1]["vid"]
        if args.limit and scanned >= args.limit:
            break
    mode = "APPLIED" if args.apply else "DRY-RUN"
    print(f"\n[{mode}] 중복 발견 {dup}건, 정리 {fixed}건")


if __name__ == "__main__":
    main()

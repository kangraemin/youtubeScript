#!/usr/bin/env python3
"""rawdata/transcripts → Supabase transcripts 테이블 upsert."""
import json
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(_ROOT / ".env.local")

os.environ.setdefault("SUPABASE_URL", os.environ.get("NEXT_PUBLIC_SUPABASE_URL", ""))
os.environ.setdefault("SUPABASE_SERVICE_KEY", os.environ.get("SUPABASE_SERVICE_ROLE_KEY", ""))

sys.path.insert(0, str(_ROOT / "worker"))
from supabase_client import get_client

TRANSCRIPTS_DIR = _ROOT / "rawdata" / "transcripts"
BATCH_SIZE = 100


def _parse_date(val: str | None) -> str | None:
    if not val:
        return None
    try:
        from datetime import date
        date.fromisoformat(val)
        return val
    except (ValueError, TypeError):
        return None


def load_channel(slug_dir: Path) -> list[dict]:
    list_file = slug_dir / "_list.json"
    if not list_file.exists():
        return []
    with open(list_file) as f:
        videos = json.load(f)

    seen = {}
    for v in videos:
        vid = v.get("vid")
        if not vid:
            continue
        txt_file = slug_dir / f"{vid}.txt"
        has_tx = txt_file.exists() and txt_file.stat().st_size > 0

        seen[vid] = {
            "vid": vid,
            "channel": v.get("channel", ""),
            "channel_slug": slug_dir.name,
            "title": v.get("title", ""),
            "published_at": _parse_date(v.get("meta")),
            "collected_at": v.get("collected_at") or None,
            # transcript 본문은 DB에 올리지 않는다 — 로컬 rawdata가 단일 소스.
            # 존재 여부만 기록(요약 큐 판정용). 본문은 get_next가 로컬에서 읽음.
            "has_transcript": has_tx,
            "url": v.get("url", ""),
        }
    return list(seen.values())


def upsert_batch(db, rows: list[dict]) -> int:
    db.table("transcripts").upsert(rows, on_conflict="vid").execute()
    return len(rows)


def main():
    db = get_client()
    total = 0

    failed = []
    for slug_dir in sorted(TRANSCRIPTS_DIR.iterdir()):
        if not slug_dir.is_dir():
            continue
        rows = load_channel(slug_dir)
        if not rows:
            print(f"  {slug_dir.name}: 0개 (skip)")
            continue

        # 채널별 격리 — 한 채널 업로드 실패가 뒤 채널을 막지 않게.
        try:
            inserted = 0
            for i in range(0, len(rows), BATCH_SIZE):
                inserted += upsert_batch(db, rows[i:i + BATCH_SIZE])
            print(f"  {slug_dir.name}: {inserted}개 upsert")
            total += inserted
        except Exception as e:
            print(f"  ⚠ {slug_dir.name}: 업로드 실패 — {e}")
            failed.append(slug_dir.name)

    print(f"\n완료: 총 {total}개")
    if failed:
        print(f"⚠ 실패 채널: {failed}")


if __name__ == "__main__":
    main()

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


def load_channel(slug_dir: Path) -> list[dict]:
    list_file = slug_dir / "_list.json"
    if not list_file.exists():
        return []
    with open(list_file) as f:
        videos = json.load(f)

    rows = []
    for v in videos:
        vid = v.get("vid")
        if not vid:
            continue
        txt_file = slug_dir / f"{vid}.txt"
        transcript = txt_file.read_text(encoding="utf-8").strip() if txt_file.exists() else None

        rows.append({
            "vid": vid,
            "channel": v.get("channel", ""),
            "channel_slug": slug_dir.name,
            "title": v.get("title", ""),
            "published_at": v.get("meta") or None,
            "collected_at": v.get("collected_at") or None,
            "transcript": transcript,
            "url": v.get("url", ""),
        })
    return rows


def upsert_batch(db, rows: list[dict]) -> int:
    db.table("transcripts").upsert(rows, on_conflict="vid").execute()
    return len(rows)


def main():
    db = get_client()
    total = 0

    for slug_dir in sorted(TRANSCRIPTS_DIR.iterdir()):
        if not slug_dir.is_dir():
            continue
        rows = load_channel(slug_dir)
        if not rows:
            print(f"  {slug_dir.name}: 0개 (skip)")
            continue

        inserted = 0
        for i in range(0, len(rows), BATCH_SIZE):
            inserted += upsert_batch(db, rows[i:i + BATCH_SIZE])
        print(f"  {slug_dir.name}: {inserted}개 upsert")
        total += inserted

    print(f"\n완료: 총 {total}개")


if __name__ == "__main__":
    main()

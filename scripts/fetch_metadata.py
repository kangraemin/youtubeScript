#!/usr/bin/env python3
"""rawdata/transcripts의 모든 video_id에 대해 YouTube videos.list 메타데이터 수집.

rawdata/metadata.json에 저장:
    {
      "video_id": {
        "published_at": "2024-12-01T10:00:00Z",
        "title": "...",
        "description": "...",
        "channel_id": "UC...",
        "thumbnail_url": "https://..."
      },
      ...
    }

Usage:
    python scripts/fetch_metadata.py               # 전체 재수집
    python scripts/fetch_metadata.py --skip-existing  # 있는 건 건너뛰기
"""
import argparse
import json
import os
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT / "worker"))

from dotenv import load_dotenv
load_dotenv(_ROOT / ".env.local")

from googleapiclient.discovery import build

_TRANSCRIPTS_DIR = _ROOT / "rawdata" / "transcripts"
_METADATA_PATH = _ROOT / "rawdata" / "metadata.json"


def collect_all_video_ids() -> list[str]:
    """rawdata/transcripts/*/*.txt 파일명에서 video_id 수집 (메타 파일 제외)."""
    vids = set()
    for path in _TRANSCRIPTS_DIR.glob("*/*.txt"):
        vid = path.stem
        if vid.startswith("_"):
            continue
        vids.add(vid)
    return sorted(vids)


def fetch_snippets_bulk(youtube, video_ids: list[str]) -> dict[str, dict]:
    """50개씩 배치로 videos.list 호출 → {vid: snippet dict}."""
    out: dict[str, dict] = {}
    for i in range(0, len(video_ids), 50):
        batch = video_ids[i:i+50]
        try:
            resp = youtube.videos().list(part="snippet", id=",".join(batch)).execute()
        except Exception as e:
            print(f"  ⚠ batch {i}-{i+len(batch)} 실패: {e}")
            continue
        got = 0
        for item in resp.get("items", []):
            s = item["snippet"]
            out[item["id"]] = {
                "published_at": s.get("publishedAt"),
                "title": s.get("title"),
                "description": s.get("description", ""),
                "channel_id": s.get("channelId"),
                "thumbnail_url": (s.get("thumbnails") or {}).get("medium", {}).get("url"),
            }
            got += 1
        print(f"  batch {i}-{i+len(batch)}: {got}/{len(batch)}")
    return out


def main():
    parser = argparse.ArgumentParser(
        description="rawdata 영상 메타데이터를 rawdata/metadata.json에 캐싱"
    )
    parser.add_argument("--skip-existing", action="store_true",
                        help="metadata.json에 이미 있는 video_id는 건너뜀")
    args = parser.parse_args()

    all_vids = collect_all_video_ids()
    print(f"rawdata video_ids: {len(all_vids)}개")

    existing: dict[str, dict] = {}
    if args.skip_existing and _METADATA_PATH.exists():
        existing = json.loads(_METADATA_PATH.read_text())
        print(f"기존 metadata: {len(existing)}개 → 스킵")
        vids_to_fetch = [v for v in all_vids if v not in existing]
    else:
        vids_to_fetch = all_vids

    print(f"가져올 video_id: {len(vids_to_fetch)}개")
    if not vids_to_fetch:
        print("할 일 없음.")
        return

    youtube = build("youtube", "v3", developerKey=os.environ["YOUTUBE_API_KEY"])
    new_meta = fetch_snippets_bulk(youtube, vids_to_fetch)
    merged = {**existing, **new_meta}

    _METADATA_PATH.parent.mkdir(parents=True, exist_ok=True)
    _METADATA_PATH.write_text(json.dumps(merged, ensure_ascii=False, indent=2))
    print(f"저장 완료: {_METADATA_PATH} ({len(merged)}개)")


if __name__ == "__main__":
    main()

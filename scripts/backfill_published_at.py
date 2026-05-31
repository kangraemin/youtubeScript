#!/usr/bin/env python3
"""published_at이 NULL인 transcripts 행을 YouTube Data API로 게시일 백필.

NULL인 행만 채운다(기존 값 덮어쓰지 않음). 채널 미지정 시 전체 NULL 대상.
삭제·비공개 등 API가 못 찾은 영상은 NULL을 유지하고 카운트만 보고한다.

Usage:
    python scripts/backfill_published_at.py --channel shukaworld
    python scripts/backfill_published_at.py            # 전체 NULL 대상
    python scripts/backfill_published_at.py --channel shukaworld --dry-run
    python scripts/backfill_published_at.py --limit 5  # API 사용 제한(테스트용)
"""
import argparse
import os
import sys
from pathlib import Path

from googleapiclient.discovery import build

_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT))

from worker.supabase_client import get_client


def fetch_null_vids(db, channel: str | None, limit: int) -> list[str]:
    """published_at IS NULL 행의 vid 수집 (range 페이지네이션)."""
    rows: list[str] = []
    start, step = 0, 1000
    while True:
        q = db.table("transcripts").select("vid").is_("published_at", "null")
        if channel:
            q = q.eq("channel_slug", channel)
        r = q.range(start, start + step - 1).execute()
        d = r.data or []
        rows += [x["vid"] for x in d]
        if len(d) < step:
            break
        start += step
    if limit:
        rows = rows[:limit]
    return rows


def fetch_published(youtube, vids: list[str]) -> dict[str, str]:
    """50개씩 배치로 videos.list 호출 → {vid: 'YYYY-MM-DD'}.

    API가 못 찾은 vid(삭제/비공개)는 결과에서 누락 → 호출측에서 NULL 유지.
    """
    out: dict[str, str] = {}
    for i in range(0, len(vids), 50):
        batch = vids[i:i + 50]
        resp = youtube.videos().list(part="snippet", id=",".join(batch)).execute()
        for item in resp.get("items", []):
            pub = item["snippet"].get("publishedAt")
            if pub:
                out[item["id"]] = pub[:10]  # YYYY-MM-DD
    return out


def main() -> int:
    ap = argparse.ArgumentParser(
        description="published_at NULL transcripts 행을 YouTube API로 백필"
    )
    ap.add_argument("--channel", help="채널 슬러그(미지정 시 전체 NULL 대상)")
    ap.add_argument("--dry-run", action="store_true", help="DB 미변경, 조회 결과만 출력")
    ap.add_argument("--limit", type=int, default=0, help="처리 vid 수 제한(테스트용)")
    args = ap.parse_args()

    db = get_client()
    vids = fetch_null_vids(db, args.channel, args.limit)
    print(f"published_at NULL 대상: {len(vids)}개 (channel={args.channel or 'ALL'})")
    if not vids:
        print("할 일 없음.")
        return 0

    youtube = build("youtube", "v3", developerKey=os.environ["YOUTUBE_API_KEY"])
    pub_map = fetch_published(youtube, vids)
    not_found = [v for v in vids if v not in pub_map]
    print(f"API 게시일 조회: {len(pub_map)}/{len(vids)}  (못 찾음: {len(not_found)})")

    if args.dry_run:
        for v, d in list(pub_map.items())[:10]:
            print(f"  [dry-run] {v} -> {d}")
        print("dry-run 종료 (DB 미변경)")
        return 0

    updated = 0
    for v, d in pub_map.items():
        # NULL인 행만 갱신 — 기존 값 보호
        (
            db.table("transcripts")
            .update({"published_at": d})
            .eq("vid", v)
            .is_("published_at", "null")
            .execute()
        )
        updated += 1
    print(f"업데이트 완료: {updated}개")
    if not_found:
        print(f"⚠ 게시일 못 찾음(삭제/비공개로 NULL 유지): {len(not_found)}개 — {not_found[:5]}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

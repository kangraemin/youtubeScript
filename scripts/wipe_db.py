#!/usr/bin/env python3
"""Supabase 수집 테이블 비우기 — restaurants, videos, processing_queue.

Usage:
    python scripts/wipe_db.py          # 확인 프롬프트
    python scripts/wipe_db.py --yes    # 확인 없이 실행

Supabase Python client는 WHERE 없는 DELETE를 막는다.
실패 시 Supabase SQL Editor에서 수동 실행:
    TRUNCATE public.videos, public.processing_queue, public.restaurants
        RESTART IDENTITY CASCADE;
"""
import argparse
import os
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT / "worker"))

from dotenv import load_dotenv
load_dotenv(_ROOT / ".env.local")

# env 이름 호환 (.env.local은 NEXT_PUBLIC_*/SUPABASE_SERVICE_ROLE_KEY 사용)
if "SUPABASE_URL" not in os.environ and "NEXT_PUBLIC_SUPABASE_URL" in os.environ:
    os.environ["SUPABASE_URL"] = os.environ["NEXT_PUBLIC_SUPABASE_URL"]
if "SUPABASE_SERVICE_KEY" not in os.environ and "SUPABASE_SERVICE_ROLE_KEY" in os.environ:
    os.environ["SUPABASE_SERVICE_KEY"] = os.environ["SUPABASE_SERVICE_ROLE_KEY"]

from supabase_client import get_client


# FK 의존성 순서: videos → processing_queue → restaurants
# (video_id, restaurant_id는 restaurants 참조)
TABLES = [
    ("videos", "restaurant_id", 0),
    ("processing_queue", "video_id", ""),
    ("restaurants", "id", 0),
]


def main():
    parser = argparse.ArgumentParser(description="Supabase 수집 테이블을 모두 비웁니다")
    parser.add_argument("--yes", action="store_true", help="확인 없이 실행")
    args = parser.parse_args()

    db = get_client()

    print("현재 데이터:")
    counts = {}
    for t, _, _ in TABLES:
        c = db.table(t).select("*", count="exact").limit(1).execute().count
        counts[t] = c
        print(f"  {t}: {c}개")

    if all(c == 0 for c in counts.values()):
        print("\n이미 모두 비어있음.")
        return

    if not args.yes:
        ans = input("\n위 테이블을 모두 비웁니다. 계속? [y/N]: ").strip().lower()
        if ans != "y":
            print("취소됨.")
            return

    failed = []
    for t, key_col, dummy in TABLES:
        try:
            if isinstance(dummy, int):
                db.table(t).delete().gte(key_col, -1).execute()
            else:
                db.table(t).delete().gte(key_col, "").execute()
            print(f"  {t} 비움 완료")
        except Exception as e:
            print(f"  ⚠ {t} 삭제 실패: {e}")
            failed.append(t)

    if failed:
        print("\n⚠ 일부 테이블 삭제 실패. Supabase SQL Editor에서 수동 실행 권장:")
        print(f"    TRUNCATE public.{', public.'.join(failed)} RESTART IDENTITY CASCADE;")
        sys.exit(1)

    print("\n확인:")
    for t, _, _ in TABLES:
        c = db.table(t).select("*", count="exact").limit(1).execute().count
        print(f"  {t}: {c}개")


if __name__ == "__main__":
    main()

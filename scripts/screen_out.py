#!/usr/bin/env python3
"""해당 vid를 요약 스크리닝 제외 처리 (screened_out=true).

비경제 콘텐츠가 섞인 채널(jisik_inside·yonhap_economy)에서 워커가 주식·경제
요약 가치 없다고 판정한 영상을 요약 큐에서 빼는 용도. 원본 transcript(로컬)·메타는 보존.

사용법:
    python scripts/screen_out.py <vid> [사유]
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from worker.supabase_client import get_client


def main() -> int:
    if len(sys.argv) < 2:
        print("usage: screen_out.py <vid> [reason]", file=sys.stderr)
        return 1
    vid = sys.argv[1]
    reason = sys.argv[2] if len(sys.argv) > 2 else ""
    get_client().table("transcripts").update({"screened_out": True}).eq("vid", vid).execute()
    print(f"screened_out: {vid}" + (f" ({reason})" if reason else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main())

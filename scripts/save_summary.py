#!/usr/bin/env python3
"""stdin/argv로 받은 summary JSON을 transcripts.summary에 UPDATE.

사용법:
    echo '<summary JSON>' | python3 scripts/save_summary.py <vid>

summary JSON에 `_model` 키가 있으면 분리해서 summary_model 컬럼에 저장.
summarized_at은 현재 UTC 시각으로 자동 채움.
"""
import json
import os
import sys
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from worker.supabase_client import get_client


def main() -> int:
    if len(sys.argv) < 2:
        print("usage: save_summary.py <vid>  (stdin에 summary JSON)", file=sys.stderr)
        return 1

    vid = sys.argv[1]
    raw = sys.stdin.read()
    summary = json.loads(raw)
    model = summary.pop("_model", "claude-sonnet-4-6")

    db = get_client()
    db.table("transcripts").update({
        "summary": summary,
        "summarized_at": datetime.now(timezone.utc).isoformat(),
        "summary_model": model,
    }).eq("vid", vid).execute()

    # 새 요약 반영 — 홈/latest 캐시 무효화 (실패해도 저장은 유지)
    try:
        import urllib.parse
        import urllib.request

        base = os.environ.get("REVALIDATE_URL")
        sec = os.environ.get("REVALIDATE_SECRET")
        if base and sec:
            u = f"{base.rstrip('/')}/api/revalidate?secret={urllib.parse.quote(sec)}"
            urllib.request.urlopen(
                urllib.request.Request(u, method="POST"), timeout=8
            ).read()
    except Exception as e:
        print(f"revalidate skip: {e}", file=sys.stderr)

    print(f"saved: {vid}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

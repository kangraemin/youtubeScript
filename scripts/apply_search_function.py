#!/usr/bin/env python3
"""create_search_function.sql을 Supabase Management API로 1회 적용.

get_next_unsummarized.py의 _env/_project_ref + database/query 엔드포인트 재사용.
"""
import json
import os
import sys
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scripts.get_next_unsummarized import _env, _project_ref


def main() -> int:
    sql_path = os.path.join(os.path.dirname(__file__), "create_search_function.sql")
    sql = open(sql_path, encoding="utf-8").read()
    pat = _env("SUPABASE_PAT")
    ref = _project_ref()
    if not pat or not ref:
        print("SUPABASE_PAT / project ref 미설정", file=sys.stderr)
        return 1
    req = urllib.request.Request(
        f"https://api.supabase.com/v1/projects/{ref}/database/query",
        data=json.dumps({"query": sql}).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {pat}",
            "Content-Type": "application/json",
            "User-Agent": "curl/8.7.1",
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        print("applied:", resp.read().decode("utf-8")[:200])
    return 0


if __name__ == "__main__":
    sys.exit(main())

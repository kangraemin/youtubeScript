#!/usr/bin/env python3
"""로컬 요약 JSON 폴더를 청크 단위 일괄 UPDATE (DB write 청크 N회).

사용법: source .env.local && python3 scripts/batch_push.py [--dir scripts/local_out] [--chunk 20]
입력: <dir>/<vid>.json  (각 파일 = save_summary.py에 넣던 13섹션 JSON, _model 포함 가능)
vid별 PATCH /rest/v1/transcripts?vid=eq.<vid> 로 갱신.
※ summary 본문이 vid마다 달라 단일 PATCH 불가 → vid별 PATCH를 청크로 묶어 순차, 청크 간 sleep.
"""
import glob
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone

DIR = "scripts/local_out"
CHUNK = 20


def _env(k: str) -> str:
    v = os.environ.get(k)
    if v:
        return v
    for p in [".env.local", os.path.expanduser("~/.claude/.env")]:
        if os.path.isfile(p):
            with open(p, encoding="utf-8") as f:
                for line in f:
                    if line.startswith(f"{k}="):
                        return line.split("=", 1)[1].strip().strip('"').strip("'")
    return ""


def _patch(url: str, key: str, vid: str, body: dict) -> int:
    req = urllib.request.Request(
        f"{url}/rest/v1/transcripts?vid=eq.{urllib.parse.quote(vid)}",
        data=json.dumps(body).encode("utf-8"),
        method="PATCH",
        headers={
            "apikey": key,
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json",
            "Prefer": "return=minimal",
            "User-Agent": "curl/8.7.1",
        },
    )
    for attempt in range(6):
        try:
            with urllib.request.urlopen(req, timeout=30) as r:
                return r.status
        except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError):
            if attempt == 5:
                raise
            time.sleep(10 * (attempt + 1))
    return 0


def main() -> int:
    d = DIR
    chunk = CHUNK
    if "--dir" in sys.argv:
        d = sys.argv[sys.argv.index("--dir") + 1]
    if "--chunk" in sys.argv:
        chunk = int(sys.argv[sys.argv.index("--chunk") + 1])

    url = _env("NEXT_PUBLIC_SUPABASE_URL") or _env("SUPABASE_URL")
    key = _env("SUPABASE_SERVICE_ROLE_KEY") or _env("SUPABASE_SERVICE_KEY")
    if not url or not key:
        print(json.dumps({"error": "SUPABASE url/key 미설정"}))
        return 1

    files = sorted(glob.glob(f"{d}/*.json"))
    ok = 0
    fail: list = []
    for i, fp in enumerate(files):
        vid = os.path.splitext(os.path.basename(fp))[0]
        with open(fp, encoding="utf-8") as f:
            summ = json.load(f)
        model = summ.pop("_model", "claude-sonnet-4-6")
        body = {
            "summary": summ,
            "summary_model": model,
            "summarized_at": datetime.now(timezone.utc).isoformat(),
        }
        try:
            _patch(url, key, vid, body)
            ok += 1
        except Exception:
            fail.append(vid)
        if (i + 1) % chunk == 0:
            time.sleep(5)  # 청크 간 텀

    print(json.dumps({"pushed": ok, "failed": fail, "total": len(files)}, ensure_ascii=False))
    return 0 if not fail else 1


if __name__ == "__main__":
    sys.exit(main())

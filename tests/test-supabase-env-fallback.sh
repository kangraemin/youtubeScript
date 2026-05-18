#!/usr/bin/env bash
# E2E: worker/supabase_client.get_client() 가 source 없이 .env.local 자동 로드 + 이름 fallback
# 실행: bash tests/test-supabase-env-fallback.sh
set -euo pipefail
cd "$(git rev-parse --show-toplevel)"
FAIL=0

echo "### TC1: source 없이, env 4종 unset 상태에서 get_client() 동작"
env -u SUPABASE_URL -u SUPABASE_SERVICE_KEY -u NEXT_PUBLIC_SUPABASE_URL \
    -u SUPABASE_SERVICE_ROLE_KEY \
    .venv/bin/python - <<'PY' || FAIL=1
import sys; sys.path.insert(0, '.')
from worker.supabase_client import get_client
c = get_client()  # .env.local 자동 로드 — KeyError 안 나야 함
assert c is not None, "client None"
print("✅ source 없이 .env.local 자동 로드 + Client 생성 OK")
PY

echo "### TC2: 이름 fallback — NEXT_PUBLIC_/_ROLE_KEY 만 있어도 해석"
env -u SUPABASE_URL -u SUPABASE_SERVICE_KEY -u NEXT_PUBLIC_SUPABASE_URL \
    -u SUPABASE_SERVICE_ROLE_KEY \
    .venv/bin/python - <<'PY' || FAIL=1
import sys; sys.path.insert(0, '.')
from worker.supabase_client import get_client
# .env.local 이 NEXT_PUBLIC_SUPABASE_URL / SUPABASE_SERVICE_ROLE_KEY 이름만 보유.
# get_client() 가 그 이름으로 fallback 해 Client 를 만들면 성공.
c = get_client()
assert type(c).__name__ == "Client", f"unexpected: {type(c).__name__}"
print("✅ NEXT_PUBLIC_/_ROLE_KEY 이름 fallback 으로 Client 생성")
PY

echo "### TC3: 자격증명 전무 시 RuntimeError (정적 코드 보장)"
grep -q 'raise RuntimeError' worker/supabase_client.py \
  && grep -q '자격 증명' worker/supabase_client.py \
  && echo "✅ RuntimeError + 자격증명 메시지 존재" || { echo "❌ 에러 경로 없음"; FAIL=1; }

echo "### TC4: py_compile + 기존 호출자 회귀"
.venv/bin/python -m py_compile worker/supabase_client.py scripts/save_summary.py \
  scripts/upload_transcripts.py scripts/backfill_summaries.py \
  && echo "✅ compile (호출자 포함)" || FAIL=1

echo "---"
[ "$FAIL" -eq 0 ] && echo "✅ E2E ALL PASS" || { echo "❌ E2E FAIL"; exit 1; }

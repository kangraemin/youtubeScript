#!/bin/bash
# tests/test-backfill-published-at.sh
# backfill_published_at.py: dry-run DB 미변경 + 실제 복구로 NULL 감소 검증
set -e
cd "$(dirname "$0")/.."
source .env.local

PASS=0; FAIL=0
check(){ if eval "$2"; then echo "✅ $1"; PASS=$((PASS+1)); else echo "❌ $1"; FAIL=$((FAIL+1)); fi; }

null_count(){
  .venv/bin/python -c "from worker.supabase_client import get_client; print(get_client().table('transcripts').select('vid',count='exact',head=True).eq('channel_slug','shukaworld').is_('published_at','null').execute().count)"
}

# TC-1 (type-check): 스크립트 문법 OK
.venv/bin/python -c "import ast; ast.parse(open('scripts/backfill_published_at.py').read())"
check "TC-1 스크립트 문법 통과" "true"

# TC-2 (e2e): dry-run 은 DB를 변경하지 않는다
BEFORE=$(null_count)
.venv/bin/python scripts/backfill_published_at.py --channel shukaworld --dry-run --limit 5 >/tmp/bf_dry.log 2>&1
AFTER_DRY=$(null_count)
check "TC-2 dry-run DB 미변경 ($BEFORE==$AFTER_DRY)" "[ \"$BEFORE\" = \"$AFTER_DRY\" ]"

# TC-3 (e2e): 실제 복구 시 NULL 카운트 감소 (소량 limit)
.venv/bin/python scripts/backfill_published_at.py --channel shukaworld --limit 5 >/tmp/bf_run.log 2>&1
AFTER_RUN=$(null_count)
check "TC-3 실제 복구로 NULL 감소 ($BEFORE -> $AFTER_RUN)" "[ \"$AFTER_RUN\" -lt \"$BEFORE\" ]"

echo "PASS=$PASS FAIL=$FAIL"
[ "$FAIL" -eq 0 ]

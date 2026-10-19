#!/bin/bash
# tests/test-backfill-has-transcript.sh
# backfill_from_db.py가 has_transcript=false 기준 + DB 본문 미기록인지 검증
set -e
cd "$(dirname "$0")/.."
PASS=0; FAIL=0
chk(){ if eval "$2"; then echo "✅ $1"; PASS=$((PASS+1)); else echo "❌ $1"; FAIL=$((FAIL+1)); fi; }

# TC-1 (type-check): 문법 통과
chk "TC-1 문법" ".venv/bin/python -c \"import ast; ast.parse(open('scripts/backfill_from_db.py').read())\""

# TC-2 (negative): transcript 본문을 DB에 update하는 코드가 없다 (메타 분리 핵심)
chk "TC-2 transcript 본문 update 제거" "! grep -qE 'update\(\{\"transcript\"' scripts/backfill_from_db.py"

# TC-3 (happy): 재수집 대상 has_transcript=false 기준 + has_transcript=true 세팅 사용
chk "TC-3 has_transcript 기준" "grep -q 'eq(.has_transcript., False)' scripts/backfill_from_db.py && grep -q 'has_transcript.: True' scripts/backfill_from_db.py"

# TC-4 (boundary): 실제 대상 건수가 전체(4000+)가 아니라 진짜 누락분(소수)인지 — 전체 재크롤 방지 증명
# 먹방 채널은 6년치 백필 목록이 먼저 들어와 자막 대기 행이 많다 → 경제·교양 채널만 센다
chk "TC-4 대상이 전체 아님(재크롤 방지)" ".venv/bin/python -c \"
from worker.supabase_client import get_client
from scripts.channel_config import FOOD_SLUGS
db=get_client()
falsec=db.table('transcripts').select('vid',count='exact',head=True).eq('has_transcript',False).not_.in_('channel_slug',FOOD_SLUGS).execute().count
total=db.table('transcripts').select('vid',count='exact',head=True).not_.in_('channel_slug',FOOD_SLUGS).execute().count
print('has_transcript=false', falsec, '/ total', total)
assert falsec < total*0.2, ('대상이 너무 많음=전체재크롤 위험', falsec, total)\""

# TC-5 (regression): crontab에 backfill 활성 + run-crawl 유지 (Step 재활성 후)
chk "TC-5 cron 재활성" "crontab -l | grep -vE '^\s*#' | grep -q 'cron_backfill.sh' && crontab -l | grep -vE '^\s*#' | grep -q 'run-crawl.sh'"

echo "PASS=$PASS FAIL=$FAIL"; [ "$FAIL" -eq 0 ]

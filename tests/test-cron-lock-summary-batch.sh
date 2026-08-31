#!/bin/bash
# tests/test-cron-lock-summary-batch.sh
# cron 중복 실행 방지 락(lockf) + 일시적 연결오류 재시도 + 요약 큐 cutoff 확장 + 요약 workflow 검증
# 배경: 2026-08-15 cron 중첩으로 소켓 고갈 → 전 채널 [Errno 49], 17일간 수집 0건.
set -e
cd "$(dirname "$0")/.."
PASS=0; FAIL=0
chk(){ if eval "$2"; then echo "✅ $1"; PASS=$((PASS+1)); else echo "❌ $1"; FAIL=$((FAIL+1)); fi; }

# ---------- Phase 1: 공유 락 ----------

# TC-1 (happy): run-crawl.sh에 lockf 가드 존재
chk "TC-1 run-crawl 락" "grep -q 'lockf' run-crawl.sh && grep -q '.crawl.lock' run-crawl.sh"

# TC-2 (happy): cron_backfill.sh가 동일한 락 파일 공유
chk "TC-2 backfill 공유락" "
  A=\$(grep -oE 'LOCK=[^ ]+' run-crawl.sh | head -1)
  B=\$(grep -oE 'LOCK=[^ ]+' scripts/cron_backfill.sh | head -1)
  [ -n \"\$A\" ] && [ \"\$A\" = \"\$B\" ]
"

# TC-3 (happy): 즉시 실패(-t 0) + 파일 유지(-k) 옵션
chk "TC-3 lockf 옵션" "grep -q 'lockf -k -s -t 0' run-crawl.sh && grep -q 'lockf -k -s -t 0' scripts/cron_backfill.sh"

# TC-4 (integration): 락 점유 중이면 두 번째 획득이 EX_TEMPFAIL(75)로 즉시 실패
chk "TC-4 중첩 스킵" "
  L=\$(mktemp -d)/t.lock
  ( /usr/bin/lockf -k -s \"\$L\" /bin/sleep 5 ) & H=\$!
  sleep 0.5
  RC=0; /usr/bin/lockf -k -s -t 0 \"\$L\" /usr/bin/true || RC=\$?
  kill -9 \$H 2>/dev/null
  [ \"\$RC\" -eq 75 ]
"

# TC-5 (negative): kill -9로 죽어도 커널이 락을 자동 해제 (shlock과 달리 stale 없음)
chk "TC-5 kill -9 자동해제" "
  L=\$(mktemp -d)/t.lock
  ( /usr/bin/lockf -k -s \"\$L\" /bin/sleep 30 ) & H=\$!
  sleep 0.5
  pkill -9 -f \"lockf -k -s \$L\" 2>/dev/null || true
  kill -9 \$H 2>/dev/null || true
  sleep 0.5
  /usr/bin/lockf -k -s -t 0 \"\$L\" /usr/bin/true
"

# TC-6 (boundary): 락 체크가 env 로드보다 먼저 (불필요한 로드 방지)
chk "TC-6 락 체크 우선" "
  L=\$(grep -n '/usr/bin/lockf' scripts/cron_backfill.sh | head -1 | cut -d: -f1)
  S=\$(grep -n 'source .env.local' scripts/cron_backfill.sh | head -1 | cut -d: -f1)
  [ \"\$L\" -lt \"\$S\" ]
"

# TC-7 (type-check): 두 셸 스크립트 문법
chk "TC-7 셸 문법" "bash -n run-crawl.sh && bash -n scripts/cron_backfill.sh"

# ---------- Phase 2: 재시도 백오프 ----------

# TC-8 (happy): call_with_retry 존재 + Errno 49 재시도 대상
chk "TC-8 재시도 유틸" "grep -q 'def call_with_retry' worker/supabase_client.py && grep -q '49' worker/supabase_client.py"

# TC-9 (negative): 비일시적 예외는 재시도하지 않고 즉시 전파
chk "TC-9 비일시적 즉시전파" "
  .venv/bin/python -c \"
import sys; sys.path.insert(0,'.')
from worker.supabase_client import call_with_retry
n=[0]
def f():
    n[0]+=1; raise ValueError('permanent')
try: call_with_retry(f, tries=5, base_delay=0)
except ValueError: pass
assert n[0]==1, f'재시도됨: {n[0]}'
\"
"

# TC-10 (happy): 일시적 오류(EADDRNOTAVAIL)는 재시도 후 성공
chk "TC-10 일시적 재시도" "
  .venv/bin/python -c \"
import sys; sys.path.insert(0,'.')
from worker.supabase_client import call_with_retry
n=[0]
def f():
    n[0]+=1
    if n[0]<3: raise OSError(49,'Cant assign requested address')
    return 'ok'
assert call_with_retry(f, tries=5, base_delay=0)=='ok'
assert n[0]==3, n[0]
\"
"

# TC-11 (boundary): tries 상한 준수 — 무한 재시도 없음
chk "TC-11 tries 상한" "
  .venv/bin/python -c \"
import sys; sys.path.insert(0,'.')
from worker.supabase_client import call_with_retry
n=[0]
def f():
    n[0]+=1; raise OSError(49,'x')
try: call_with_retry(f, tries=3, base_delay=0)
except OSError: pass
assert n[0]==3, n[0]
\"
"

# TC-12 (negative): 순환 예외 체인에서도 무한루프 없이 판정 종료
chk "TC-12 순환체인 안전" "
  .venv/bin/python -c \"
import sys; sys.path.insert(0,'.')
from worker.supabase_client import _is_transient
a=RuntimeError('a'); b=RuntimeError('b')
a.__cause__=b; b.__cause__=a
assert _is_transient(a) is False
\"
"

# TC-13 (happy): 8/15 실제 사고 지점 두 곳이 모두 재시도로 감싸짐
chk "TC-13 사고지점 적용" "grep -q 'call_with_retry' scripts/backfill_from_db.py && grep -A5 'def upsert_batch' scripts/upload_transcripts.py | grep -q 'call_with_retry'"

# ---------- Phase 3: 요약 큐 cutoff ----------

# TC-14 (happy): cutoff 환경변수 오버라이드
chk "TC-14 cutoff env" "
  .venv/bin/python -c \"
import os, importlib.util
os.environ['SUMMARY_CUTOFF_DAYS']='3650'
spec=importlib.util.spec_from_file_location('g','scripts/get_next_unsummarized.py')
m=importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
assert m.CUTOFF_DAYS==3650, m.CUTOFF_DAYS
\"
"

# TC-15 (regression): 미설정 시 기본 30 유지 — 기존 cron 동작 불변
chk "TC-15 기본 30 유지" "
  .venv/bin/python -c \"
import os, importlib.util
os.environ.pop('SUMMARY_CUTOFF_DAYS', None)
spec=importlib.util.spec_from_file_location('g','scripts/get_next_unsummarized.py')
m=importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
assert m.CUTOFF_DAYS==30, m.CUTOFF_DAYS
\"
"

# TC-16 (boundary): 큐 정렬이 최근순(published_at DESC) 유지
chk "TC-16 최근순 정렬" "grep -q 'ORDER BY published_at DESC' scripts/get_next_unsummarized.py"

# TC-17 (regression): 동시 claim 안전장치가 그대로 유지됨
chk "TC-17 원자 claim 유지" "grep -q 'FOR UPDATE SKIP LOCKED' scripts/get_next_unsummarized.py && grep -q 'summary_started_at' scripts/get_next_unsummarized.py"

# ---------- Phase 4: 요약 workflow ----------

# TC-18 (happy): workflow 파일 + meta 리터럴
chk "TC-18 workflow meta" "test -f .claude/workflows/summarize-batch.js && grep -q 'export const meta' .claude/workflows/summarize-batch.js"

# TC-19 (type-check): workflow 스크립트 구문
chk "TC-19 workflow 문법" "node --check .claude/workflows/summarize-batch.js"

# TC-20 (happy): 요약 절차 4요소가 에이전트 프롬프트에 포함
chk "TC-20 절차 4요소" "
  W=.claude/workflows/summarize-batch.js
  grep -q get_next_unsummarized \$W && grep -q screen_out \$W && grep -q save_summary \$W && grep -q SUMMARY_CUTOFF_DAYS \$W
"

# TC-21 (negative): 에이전트 null 반환 시에도 집계가 깨지지 않음
chk "TC-21 null 방어" "grep -q 'results.filter(Boolean)' .claude/workflows/summarize-batch.js"

echo "PASS=$PASS FAIL=$FAIL"; [ "$FAIL" -eq 0 ]

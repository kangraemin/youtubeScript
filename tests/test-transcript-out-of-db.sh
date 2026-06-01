#!/bin/bash
# tests/test-transcript-out-of-db.sh
# transcript 본문 DB 분리(로컬 단일 소스) 검증
set -e
cd "$(dirname "$0")/.."
PASS=0; FAIL=0
chk(){ if eval "$2"; then echo "✅ $1"; PASS=$((PASS+1)); else echo "❌ $1"; FAIL=$((FAIL+1)); fi; }

# TC-1 (integration): has_transcript 컬럼 존재 + backfill 정합 (true 개수 >= transcript NOT NULL 개수)
chk "TC-1 has_transcript backfill 정합" ".venv/bin/python -c \"
from worker.supabase_client import get_client
db=get_client()
a=db.table('transcripts').select('vid',count='exact',head=True).eq('has_transcript',True).execute().count
b=db.table('transcripts').select('vid',count='exact',head=True).not_.is_('transcript','null').execute().count
assert a>=b, (a,b)
print('has_transcript',a,'>= transcript NOT NULL',b)\""

# TC-2 (e2e): upload 메타전용 — 전 채널 완주(크래시 없이), timeout 없음
chk "TC-2 upload 완주" ".venv/bin/python scripts/upload_transcripts.py > /tmp/up.log 2>&1; tail -3 /tmp/up.log; grep -q '완료: 총' /tmp/up.log"

# TC-3 (e2e): 누락됐던 yonhap 신규분이 업로드됨 (DB 최신 published_at 전진)
chk "TC-3 yonhap 신규 적재" ".venv/bin/python -c \"
from worker.supabase_client import get_client
db=get_client()
r=db.table('transcripts').select('published_at').eq('channel_slug','yonhap_economy').order('published_at',desc=True).limit(1).execute()
latest=r.data[0]['published_at']
print('yonhap 최신',latest)
assert latest >= '2026-05-31', latest\""

# TC-4 (e2e): get_next가 DB본문 없이 로컬에서 읽어 transcript_path 반환 (claim 가능분 있을 때)
chk "TC-4 get_next 로컬읽기" ".venv/bin/python -c \"
import json,subprocess
out=subprocess.run(['.venv/bin/python','scripts/get_next_unsummarized.py'],capture_output=True,text=True).stdout.strip().splitlines()[-1]
d=json.loads(out)
assert d.get('empty') or (d.get('transcript_path') and d.get('transcript_chars',0)>0), d
print('get_next ok:', 'empty' if d.get('empty') else d['transcript_path'])\""

# TC-5 (negative): upload row dict에 transcript 본문 키 없음(메타전용) — load_channel이 has_transcript만 넣음
chk "TC-5 메타전용(transcript 본문 미upsert)" "grep -q 'has_transcript' scripts/upload_transcripts.py && ! grep -qE '\"transcript\"[[:space:]]*:[[:space:]]*transcript' scripts/upload_transcripts.py"

# TC-6 (boundary): has_transcript=true·로컬파일 없는 가짜행 주입 시 get_next가 park(2099)+무한루프 없음. 끝나면 원복.
chk "TC-6 로컬파일 없으면 park + 무한루프 없음" ".venv/bin/python - <<'PY'
import subprocess, time
from worker.supabase_client import get_client
db=get_client()
VID='__test_missing_local__'
db.table('transcripts').upsert({'vid':VID,'channel':'t','channel_slug':'moneycomics','title':'t','published_at':'2026-06-01','has_transcript':True,'summary':None,'summary_started_at':None},on_conflict='vid').execute()
try:
    t0=time.time()
    subprocess.run(['.venv/bin/python','scripts/get_next_unsummarized.py'],capture_output=True,text=True,timeout=120)
    assert time.time()-t0 < 120, 'timeout(무한루프 의심)'
    row=db.table('transcripts').select('summary_started_at').eq('vid',VID).single().execute().data
    assert str(row['summary_started_at']).startswith('2099'), ('park 안 됨', row)
    print('park OK, no infinite loop')
finally:
    db.table('transcripts').delete().eq('vid',VID).execute()
PY"

# TC-7 (type-check): 웹 tsc 통과 (서브셸로 cd 누수 방지)
chk "TC-7 web tsc" "(cd web && npx tsc --noEmit)"

# TC-8 (regression): 웹 상세페이지 원본 transcript 렌더 블록 제거 + 요약 유지
# 경로의 [vid]가 bash glob으로 해석되지 않게 단일따옴표로 감쌈
chk "TC-8 웹 원본블록 제거" "! grep -q 't.transcript' 'web/app/video/[vid]/page.tsx' && grep -q 'SummaryCard' 'web/app/video/[vid]/page.tsx'"

echo "PASS=$PASS FAIL=$FAIL"; [ "$FAIL" -eq 0 ]

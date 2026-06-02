#!/bin/bash
# tests/test-summary-screening.sh
# jisik_inside·yonhap_economy 요약 스크리닝(screened_out) 검증
set -e
cd "$(dirname "$0")/.."
PASS=0; FAIL=0
chk(){ if eval "$2"; then echo "✅ $1"; PASS=$((PASS+1)); else echo "❌ $1"; FAIL=$((FAIL+1)); fi; }

# TC-1 (integration): screened_out 컬럼 존재
chk "TC-1 screened_out 컬럼" ".venv/bin/python -c \"
from worker.supabase_client import get_client
db=get_client()
print('false count', db.table('transcripts').select('vid',count='exact',head=True).eq('screened_out',False).execute().count)\""

# TC-2 (happy): SCREEN_SLUGS = jisik_inside·yonhap_economy (그 외 미포함)
chk "TC-2 SCREEN_SLUGS 정의" ".venv/bin/python -c \"
from scripts.channel_config import SCREEN_SLUGS
assert SCREEN_SLUGS=={'jisik_inside','yonhap_economy'}, SCREEN_SLUGS
assert 'shukaworld' not in SCREEN_SLUGS and 'moneycomics' not in SCREEN_SLUGS
print('SCREEN_SLUGS', SCREEN_SLUGS)\""

# TC-3 (happy): get_next 큐 SQL이 screened_out=false 포함
chk "TC-3 get_next screened_out 제외" "grep -q 'screened_out = false' scripts/get_next_unsummarized.py"

# TC-4 (e2e): screen_out.py가 screened_out=true 세팅하고 그 행이 get_next 큐에서 빠진다
chk "TC-4 screen_out → 큐 제외" ".venv/bin/python - <<'PY'
import subprocess
from worker.supabase_client import get_client
db=get_client()
VID='__test_screen__'
db.table('transcripts').upsert({'vid':VID,'channel':'t','channel_slug':'jisik_inside','title':'t','published_at':'2026-06-02','has_transcript':True,'summary':None,'summary_started_at':None,'screened_out':False},on_conflict='vid').execute()
try:
    def claimable():
        return db.table('transcripts').select('vid',count='exact',head=True).eq('vid',VID).is_('summary','null').eq('has_transcript',True).eq('screened_out',False).execute().count
    before=claimable()
    subprocess.run(['.venv/bin/python','scripts/screen_out.py',VID,'test'],capture_output=True,text=True,check=True)
    row=db.table('transcripts').select('screened_out').eq('vid',VID).single().execute().data
    after=claimable()
    assert row['screened_out'] is True, row
    assert before==1 and after==0, (before,after)
    print('screen_out OK: claimable', before, '->', after)
finally:
    db.table('transcripts').delete().eq('vid',VID).execute()
PY"

# TC-5 (regression): 순수경제·shukaworld는 SCREEN_SLUGS 미포함
chk "TC-5 비대상 채널 보존" ".venv/bin/python -c \"
from scripts.channel_config import SCREEN_SLUGS, SUMMARY_SLUGS
non=[s for s in SUMMARY_SLUGS if s not in SCREEN_SLUGS]
assert 'shukaworld' in non and 'moneycomics' in non and 'developmong' in non
print('스크리닝 비대상', non)\""

# TC-6 (happy): summarize-next.md에 스크리닝 스텝 + screen_out.py 존재
chk "TC-6 summarize-next 스크리닝 스텝" "grep -q '스크리닝' .claude/commands/summarize-next.md && grep -q 'screen_out.py' .claude/commands/summarize-next.md"

echo "PASS=$PASS FAIL=$FAIL"; [ "$FAIL" -eq 0 ]

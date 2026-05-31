#!/bin/bash
# tests/test-add-channel-aspim.sh
# @ASPIM_research 채널 등록 정합성 + handle ground-truth + DB 적재 검증
set -e
cd "$(dirname "$0")/.."
PASS=0; FAIL=0
check(){ if eval "$2"; then echo "✅ $1"; PASS=$((PASS+1)); else echo "❌ $1"; FAIL=$((FAIL+1)); fi; }

# TC-1 (happy): CHANNELS 리스트에 aspim_research 등록됨
check "TC-1 CHANNELS 등록" "grep -q 'aspim_research' scripts/crawl_youtube_transcripts.py"

# TC-2 (integration): SUMMARY_SLUGS에 aspim_research 포함 + invest_media 분류 (요약 큐 자동 진입)
check "TC-2 SUMMARY_SLUGS 포함" ".venv/bin/python -c \"from scripts.channel_config import SUMMARY_SLUGS,category_of; assert 'aspim_research' in SUMMARY_SLUGS; assert category_of('aspim_research')=='invest_media'\""

# TC-3 (happy): 웹 CHANNEL_META 등록 (피드 표시)
check "TC-3 web CHANNEL_META 등록" "grep -q 'aspim_research' web/lib/channels.ts"

# TC-4 (e2e): @handle ground-truth 해석 성공 (다른 채널 아님)
check "TC-4 handle 해석" ".venv/bin/python -c \"from dotenv import load_dotenv; load_dotenv('.env.local'); import os; from googleapiclient.discovery import build; yt=build('youtube','v3',developerKey=os.environ['YOUTUBE_API_KEY']); items=yt.channels().list(part='snippet',forHandle='ASPIM_research').execute().get('items',[]); assert items, 'handle resolve fail'; print(items[0]['snippet']['title'])\""

# TC-5 (e2e): 크롤+업로드 후 DB에 aspim_research transcript 적재됨
N=$(.venv/bin/python -c "from worker.supabase_client import get_client; print(get_client().table('transcripts').select('vid',count='exact',head=True).eq('channel_slug','aspim_research').execute().count)")
check "TC-5 DB 적재 ($N건)" "[ \"$N\" -gt 0 ]"

echo "PASS=$PASS FAIL=$FAIL"
[ "$FAIL" -eq 0 ]

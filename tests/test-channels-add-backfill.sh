#!/usr/bin/env bash
# E2E: 매경 월가월부·교양이를 부탁해 채널 추가 + 신규 카테고리
# 실행: bash tests/test-channels-add-backfill.sh
set -euo pipefail
cd "$(git rev-parse --show-toplevel)"
FAIL=0

echo "### TC1: channel_config 신규 카테고리 정책"
python3 -c "
import sys; sys.path.insert(0,'.')
from scripts.channel_config import (policy_for, category_of, SUMMARY_SLUGS,
    INVEST_MEDIA_SLUGS, CULTURE_SLUGS, EXCLUDED_FROM_SUMMARY)
assert category_of('mk_wallstreet') == 'invest_media'
assert category_of('sbs_gyoyangi') == 'culture'
assert policy_for('mk_wallstreet') == {'days':30,'summary':True,'min_duration_sec':180}
assert policy_for('sbs_gyoyangi') == {'days':30,'summary':True,'min_duration_sec':180}
assert 'mk_wallstreet' in SUMMARY_SLUGS and 'sbs_gyoyangi' in SUMMARY_SLUGS
assert 'mk_wallstreet' not in EXCLUDED_FROM_SUMMARY and 'sbs_gyoyangi' not in EXCLUDED_FROM_SUMMARY
print('OK')
" || FAIL=1

echo "### TC2: 기존 채널 정책 무변경 (regression)"
python3 -c "
import sys; sys.path.insert(0,'.')
from scripts.channel_config import policy_for, category_of
assert category_of('yonhap_economy')=='news' and policy_for('yonhap_economy')['min_duration_sec']==180
assert policy_for('moneycomics_videos')['min_duration_sec']==0 and policy_for('moneycomics_videos')['days']==30
assert policy_for('tzuyang')['days']==60 and policy_for('sampro_tv')['days']==60
assert policy_for('unknown')['days']==30
print('OK')
" || FAIL=1

echo "### TC3: CHANNELS 리스트 신규 채널 id/tab"
python3 -c "
import sys; sys.path.insert(0,'.')
from scripts.crawl_youtube_transcripts import CHANNELS
m={c['slug']:c for c in CHANNELS}
assert m['mk_wallstreet']['id']=='UCIipmgxpUxDmPP-ma3Ahvbw' and m['mk_wallstreet']['tab']=='videos'
assert m['sbs_gyoyangi']['id']=='UChY8VUjXv0aA7RF9hDQ0ISg' and m['sbs_gyoyangi']['tab']=='videos'
print('OK')
" || FAIL=1

echo "### TC4: 슬러그 정합성 CHANNELS↔channel_config"
python3 -c "
import sys; sys.path.insert(0,'.')
from scripts.crawl_youtube_transcripts import CHANNELS
from scripts.channel_config import category_of
for s in ('mk_wallstreet','sbs_gyoyangi'):
    assert any(c['slug']==s for c in CHANNELS)
    assert category_of(s)!='other'
print('OK')
" || FAIL=1

echo "### TC5: web 메타 + py_compile"
grep -q 'mk_wallstreet:' web/lib/channels.ts && grep -q 'sbs_gyoyangi:' web/lib/channels.ts && echo 'web메타OK' || FAIL=1
python3 -m py_compile scripts/channel_config.py scripts/crawl_youtube_transcripts.py && echo 'compileOK' || FAIL=1

echo "---"
[ "$FAIL" -eq 0 ] && echo "✅ E2E ALL PASS" || { echo "❌ FAIL"; exit 1; }

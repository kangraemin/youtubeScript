#!/usr/bin/env bash
# E2E: 연합뉴스 쇼츠 영구 제외 정책
# 실행: bash tests/test-yonhap-shorts-exclude.sh
set -euo pipefail
cd "$(git rev-parse --show-toplevel)"
FAIL=0

echo "### TC1: channel_config 정책"
python3 -c "
import sys; sys.path.insert(0,'.')
from scripts.channel_config import (policy_for, category_of, SUMMARY_SLUGS,
    STOCK_ECON_SLUGS, NEWS_SLUGS, EXCLUDED_FROM_SUMMARY)
assert category_of('yonhap_economy') == 'news'
assert policy_for('yonhap_economy')['min_duration_sec'] == 180
assert policy_for('yonhap_economy')['summary'] is True
assert policy_for('moneycomics_videos')['min_duration_sec'] == 0
assert policy_for('tzuyang')['min_duration_sec'] == 0
assert 'yonhap_economy' not in STOCK_ECON_SLUGS
assert 'yonhap_economy' in NEWS_SLUGS
assert 'yonhap_economy' in SUMMARY_SLUGS
assert set(SUMMARY_SLUGS) == set(STOCK_ECON_SLUGS) | set(NEWS_SLUGS)
assert 'yonhap_economy' not in EXCLUDED_FROM_SUMMARY
print('✅ 정책 OK')
" || FAIL=1

echo "### TC2: 쇼츠 필터 함수"
python3 -c "
import sys; sys.path.insert(0,'.')
from scripts.crawl_youtube_transcripts import _iso_dur_sec
assert _iso_dur_sec('PT45S')==45 and _iso_dur_sec('PT3M20S')==200 and _iso_dur_sec('PT1H2M3S')==3723
assert _iso_dur_sec('PT0S')==0 and _iso_dur_sec(None)==0
print('✅ duration 파서 OK')
" || FAIL=1
grep -q '_filter_by_min_duration' scripts/crawl_youtube_transcripts.py && echo "✅ 필터 함수 존재" || FAIL=1
grep -q 'min_dur > 0 and videos' scripts/crawl_youtube_transcripts.py && echo "✅ get_channel_videos_api 연동" || FAIL=1

echo "### TC3: 큐 SUMMARY_SLUGS 사용"
grep -q 'from scripts.channel_config import SUMMARY_SLUGS' scripts/get_next_unsummarized.py && echo "✅ get_next import" || FAIL=1
grep -q 'from scripts.channel_config import SUMMARY_SLUGS' scripts/dump_pending.py && echo "✅ dump import" || FAIL=1
grep -q 'STOCK_ECON_SLUGS' scripts/get_next_unsummarized.py && { echo "❌ get_next STOCK 잔존"; FAIL=1; } || echo "✅ get_next STOCK 미사용"
grep -q 'STOCK_ECON_SLUGS' scripts/dump_pending.py && { echo "❌ dump STOCK 잔존"; FAIL=1; } || echo "✅ dump STOCK 미사용"

echo "### TC4: py_compile 전체"
python3 -m py_compile scripts/channel_config.py scripts/crawl_youtube_transcripts.py \
  scripts/get_next_unsummarized.py scripts/dump_pending.py && echo "✅ compile" || FAIL=1

echo "### TC5: regression — 기존 채널 정책 무변경"
python3 -c "
import sys; sys.path.insert(0,'.')
from scripts.channel_config import policy_for
assert policy_for('moneycomics_videos')['days']==30
assert policy_for('tzuyang')['days']==60
assert policy_for('sampro_tv')['days']==60
assert policy_for('unknown')['days']==30
print('✅ 기존 채널 정책 무변경')
" || FAIL=1

echo "---"
[ "$FAIL" -eq 0 ] && echo "✅ E2E ALL PASS" || { echo "❌ E2E FAIL"; exit 1; }

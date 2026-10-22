#!/bin/bash
# tests/test-channel-config.sh
# 채널 정의 단일화: slug 중복 없음, 백종원 제외, FOOD_SLUGS ⊂ CHANNELS, 사용처 import 성공
set -e
cd "$(dirname "$0")/.."
PASS=0; FAIL=0
check(){ if eval "$2"; then echo "✅ $1"; PASS=$((PASS+1)); else echo "❌ $1"; FAIL=$((FAIL+1)); fi; }
PY=".venv/bin/python -c"

check "TC-1 slug 중복 없음" "$PY \"from scripts.channel_config import CHANNELS as C; s=[c['slug'] for c in C]; assert len(s)==len(set(s))\""
check "TC-2 id 중복 없음(handle로 찾는 빈 id 제외)" "$PY \"from scripts.channel_config import CHANNELS as C; s=[c['id'] for c in C if c['id']]; assert len(s)==len(set(s))\""
check "TC-3 백종원 제외" "$PY \"from scripts.channel_config import CHANNELS as C; assert all(c['id']!='UCyn-K7rZLXjGl7VXGweIlcA' for c in C)\""
check "TC-4 FOOD_SLUGS ⊂ CHANNELS (13개)" "$PY \"from scripts.channel_config import CHANNELS as C, FOOD_SLUGS as F, food_channels; assert set(F)<={c['slug'] for c in C} and len(food_channels())==13\""
check "TC-5 먹을텐데 제목 필터" "$PY \"from scripts.channel_config import CHANNELS as C; assert next(c for c in C if c['slug']=='sungsikyung')['title_include']=='먹을텐데'\""
check "TC-5b 또간집은 스튜디오 수제 채널의 '또간집' 회차만" "$PY \"from scripts.channel_config import CHANNELS as C; c=next(c for c in C if c['slug']=='ttoganjip'); assert c['id']=='UC4ZA57iJrf73bJlApKFeLRw' and c['title_include']=='또간집'\""
check "TC-5c 정육왕 채널" "$PY \"from scripts.channel_config import CHANNELS as C; assert next(c for c in C if c['slug']=='jeongyukwang')['id']=='UC1oXmhvYHVI2bApphh3IzuQ'\""
check "TC-5e 하이갱스·서울 사는 남자·회사랑 채널" "$PY \"from scripts.channel_config import food_channels as F; ids={c['slug']:c['id'] for c in F()}; assert ids['higaengs']=='UC86GzuZXRb7aZnhnnUA3IAg' and ids['seoul_namzaa']=='UCB6rLbWzClupm4FshWTnPRA' and ids['rawfisheater']=='UCoLPofyAZuuq6v4EWrWRguw'\""
check "TC-5d 맛집 백필 크론이 채널을 설정에서 읽는다(사본 목록 없음)" "! grep -q 'FOOD=\"dulcinea' scripts/cron_food_backfill.sh && grep -q 'FOOD_SLUGS' scripts/cron_food_backfill.sh"
check "TC-6 crawl import" "$PY \"import scripts.crawl_youtube_transcripts\""
check "TC-7 pipeline import" "$PY \"import sys; sys.path.insert(0,'worker'); import pipeline\""
check "TC-8 whisper import" "$PY \"import scripts.whisper_fallback\""
check "TC-9 사본 정의 없음" "! grep -l '^CHANNELS *= *\[' scripts/*.py worker/*.py | grep -v channel_config.py"

echo "PASS=$PASS FAIL=$FAIL"
[ "$FAIL" -eq 0 ]

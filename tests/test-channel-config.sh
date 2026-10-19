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
check "TC-4 FOOD_SLUGS ⊂ CHANNELS (8개)" "$PY \"from scripts.channel_config import CHANNELS as C, FOOD_SLUGS as F, food_channels; assert set(F)<={c['slug'] for c in C} and len(food_channels())==8\""
check "TC-5 먹을텐데 제목 필터" "$PY \"from scripts.channel_config import CHANNELS as C; assert next(c for c in C if c['slug']=='sungsikyung')['title_include']=='먹을텐데'\""
check "TC-6 crawl import" "$PY \"import scripts.crawl_youtube_transcripts\""
check "TC-7 pipeline import" "$PY \"import sys; sys.path.insert(0,'worker'); import pipeline\""
check "TC-8 whisper import" "$PY \"import scripts.whisper_fallback\""
check "TC-9 사본 정의 없음" "! grep -l '^CHANNELS *= *\[' scripts/*.py worker/*.py | grep -v channel_config.py"

echo "PASS=$PASS FAIL=$FAIL"
[ "$FAIL" -eq 0 ]

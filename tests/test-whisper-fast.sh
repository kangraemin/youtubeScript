#!/bin/bash
# tests/test-whisper-fast.sh
# 2배속 받아쓰기: 시각을 원래 속도로 되돌리고, 같은 말 되풀이와 외국 글자 섞인 줄은 버린다
set -e
cd "$(dirname "$0")/.."
PASS=0; FAIL=0
check(){ if eval "$2"; then echo "✅ $1"; PASS=$((PASS+1)); else echo "❌ $1"; FAIL=$((FAIL+1)); fi; }

check "TC-1 2배속 시각을 2배로 되돌린다" ".venv/bin/python -c \"
from scripts.whisper_fallback import clean_segments
r=clean_segments([{'start':30.4,'text':' 코카콜라 주세요'},{'start':61,'text':'열심히 공부했는데'}], 2.0)
assert r==[{'timestamp':'1:00','text':'코카콜라 주세요'},{'timestamp':'2:02','text':'열심히 공부했는데'}], r\""

check "TC-2 바로 앞과 같은 말·빈 줄·키릴/아랍 글자 섞인 줄은 버린다" ".venv/bin/python -c \"
from scripts.whisper_fallback import clean_segments
s=[{'start':1,'text':'한 번씩.'},{'start':2,'text':'한 번씩.'},{'start':3,'text':' '},{'start':4,'text':'혼자 뽑 разг morgen'},{'start':5,'text':'사람들이 ث 최고'},{'start':6,'text':'Can I get one burger?'},{'start':7,'text':'한 번씩.'}]
r=[x['text'] for x in clean_segments(s, 1.0)]
assert r==['한 번씩.','Can I get one burger?','한 번씩.'], r\""

check "TC-3 오디오는 변환 없이 원본(bestaudio)으로 받고 2배속·이전문맥 끔으로 받아 적는다" "grep -q -- '\"-f\", \"bestaudio\"' scripts/whisper_fallback.py && ! grep -q -- '--audio-format' scripts/whisper_fallback.py && grep -q 'atempo' scripts/whisper_fallback.py && grep -q 'condition_on_previous_text=False' scripts/whisper_fallback.py"

echo "PASS=$PASS FAIL=$FAIL"
[ "$FAIL" -eq 0 ]

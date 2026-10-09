#!/bin/bash
# tests/test-summarize-batch-fanout.sh
# summarize-batch.js: queue 인자로 에이전트 수를 줄이는지 + 스크리닝 채널이 SCREEN_SLUGS와 일치하는지
set -e
cd "$(dirname "$0")/.."
PASS=0; FAIL=0
chk(){ if eval "$2"; then echo "✅ $1"; PASS=$((PASS+1)); else echo "❌ $1"; FAIL=$((FAIL+1)); fi; }
WF=.claude/workflows/summarize-batch.js

# 스크립트 상단의 인자 해석부만 떼어 node로 평가한다(agent/parallel 런타임 없이).
# 인자는 JSON 문자열로 환경변수에 넘긴다(셸 따옴표·중괄호 확장을 피한다).
fanout(){ WF_ARGS="$1" node -e '
const src = require("fs").readFileSync(process.argv[1], "utf8")
const head = src.slice(src.indexOf("const MAX_FANOUT"), src.indexOf("const RESULT_SCHEMA"))
const fn = new Function("args", head + "; return FANOUT")
console.log(fn(JSON.parse(process.env.WF_ARGS)))' "$WF"; }

chk "TC-1 queue=1 → 에이전트 1명" '[ "$(fanout '"'"'{"fanout":8,"perAgent":3,"queue":1}'"'"')" = 1 ]'
chk "TC-2 queue=7 → ceil(7/3)=3명" '[ "$(fanout '"'"'{"fanout":8,"perAgent":3,"queue":7}'"'"')" = 3 ]'
chk "TC-3 queue=100 → 상한 8명" '[ "$(fanout '"'"'{"fanout":8,"perAgent":3,"queue":100}'"'"')" = 8 ]'
chk "TC-4 queue 없으면 fanout 그대로(하위 호환)" '[ "$(fanout '"'"'{"fanout":8,"perAgent":3}'"'"')" = 8 ]'
chk "TC-5 queue=0 → 최소 1명" '[ "$(fanout '"'"'{"fanout":8,"perAgent":3,"queue":0}'"'"')" = 1 ]'

# TC-6: 워크플로 프롬프트의 스크리닝 채널 = channel_config.SCREEN_SLUGS
chk "TC-6 스크리닝 채널 일치" ".venv/bin/python - <<'PY'
import re, sys; sys.path.insert(0, '.')
from scripts.channel_config import SCREEN_SLUGS
src = open('$WF', encoding='utf-8').read()
line = next(l for l in src.splitlines() if l.strip().startswith('2. 스크리닝'))
found = set(re.findall(r'[a-z_]+', line.split('channel_slug가')[1].split('일 때만')[0]))
assert found == SCREEN_SLUGS, (found, SCREEN_SLUGS)
PY"

# TC-7: 콩트·상황극 제외 기준이 워크플로와 summarize-next 양쪽에 있다
chk "TC-7 콩트 제외 기준" "grep -q '콩트·상황극' $WF && grep -q '콩트·상황극' .claude/commands/summarize-next.md"

# TC-8: 워크플로가 v3 스키마를 지시한다(13섹션 지시 잔재 없음)
chk "TC-8 v3 지시" "grep -q '\"schema\": \"v3\"' $WF && ! grep -q '13섹션' $WF"

echo "PASS=$PASS FAIL=$FAIL"; [ "$FAIL" -eq 0 ]

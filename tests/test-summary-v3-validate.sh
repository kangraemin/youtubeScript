#!/bin/bash
# tests/test-summary-v3-validate.sh
# save_summary.py v3 검증(validate_v3) — DB 없이 순수 함수로 검사한다
set -e
cd "$(dirname "$0")/.."
PASS=0; FAIL=0
chk(){ if eval "$2"; then echo "✅ $1"; PASS=$((PASS+1)); else echo "❌ $1"; FAIL=$((FAIL+1)); fi; }

PY=".venv/bin/python"
T='$PY - <<'"'"'PY'"'"'
import sys; sys.path.insert(0, ".")
from scripts.save_summary import validate_v3
RAW = "제목\nhttps://x\nvideo_id: v\n\n" + "\n".join(
    f"{m}:{s:02d} 오늘은 큰 액션 하지 말고 보시죠 {m}{s}" for m in range(0, 10) for s in range(0, 60, 5))
def ok(**kw):
    base = {"schema": "v3", "content_type": "market_brief", "tldr": "관망이 최선",
            "watch_guide": {"verdict": "skim", "why": "요약으로 충분"},
            "key_points": [{"id": "k1", "point": "관망", "detail": "d", "ts": "0:05", "quote": "오늘은 큰 액션 하지 말고 보시죠 05"}],
            "chapters": [{"ts": "0:00", "title": "시작"}, {"ts": "9:00", "title": "끝"}]}
    base.update(kw); return base
'

# TC-1 (happy): 규칙을 지킨 v3는 위반 0
chk "TC-1 정상 v3 통과" "$T
assert validate_v3(ok(), RAW) == [], validate_v3(ok(), RAW)
PY"

# TC-2 (fail): transcript에 없는 quote는 위반
chk "TC-2 지어낸 quote 차단" "$T
e = validate_v3(ok(key_points=[{\"id\":\"k1\",\"point\":\"p\",\"quote\":\"전혀 없는 발언입니다\"}]), RAW)
assert any(\"transcript에 없음\" in x for x in e), e
PY"

# TC-3 (fail): 같은 quote 두 번은 위반
chk "TC-3 quote 중복 차단" "$T
q = \"오늘은 큰 액션 하지 말고 보시죠 05\"
e = validate_v3(ok(key_points=[{\"id\":\"k1\",\"point\":\"a\",\"quote\":q},{\"id\":\"k2\",\"point\":\"b\",\"quote\":q}]), RAW)
assert any(\"중복\" in x for x in e), e
PY"

# TC-4 (fail): chapters가 후반 85%에 못 미치면 위반
chk "TC-4 후반부 커버리지" "$T
e = validate_v3(ok(chapters=[{\"ts\":\"0:00\",\"title\":\"a\"},{\"ts\":\"3:00\",\"title\":\"b\"}]), RAW)
assert any(\"85%\" in x for x in e), e
PY"

# TC-5 (fail): 분량 상한(max(25%, 4000자)) 초과는 위반
chk "TC-5 분량 상한" "$T
e = validate_v3(ok(key_points=[{\"id\":f\"k{i}\",\"point\":\"p\",\"detail\":\"가\"*600} for i in range(10)]), RAW)
assert any(\"상한\" in x for x in e), e
PY"

# TC-6 (fail): positions에 quote 없거나 action 오타면 위반
chk "TC-6 positions 규칙" "$T
e = validate_v3(ok(positions=[{\"asset\":\"삼성전자\",\"action\":\"buyy\"}]), RAW)
assert any(\"action\" in x for x in e) and any(\"quote 필수\" in x for x in e), e
PY"

# TC-7 (edge): entertainment는 key_points 3개 초과 금지, chapters 커버리지 면제
chk "TC-7 entertainment 축약" "$T
e = validate_v3(ok(content_type=\"entertainment\", chapters=[]), RAW)
assert e == [], e
e = validate_v3(ok(content_type=\"entertainment\", key_points=[{\"id\":f\"k{i}\",\"point\":\"p\"} for i in range(4)]), RAW)
assert any(\"1~3개\" in x for x in e), e
PY"

# TC-8 (edge): transcript를 못 찾으면 원문 대조는 건너뛰고 구조 검사만
chk "TC-8 transcript 없음" "$T
assert validate_v3(ok(), None) == []
PY"

# TC-9 (regression): 손으로 쓴 v3 모범 샘플(iQ2zUAaGoEw)은 통과
chk "TC-9 모범 샘플 통과" "$PY - <<'PY'
import json, sys; sys.path.insert(0, '.')
from scripts.save_summary import validate_v3, find_transcript
s = json.load(open('docs/reviews/2026-10-05/v3/iQ2zUAaGoEw.v3.json'))
t = find_transcript('iQ2zUAaGoEw')
assert t is not None
assert validate_v3(s, t) == [], validate_v3(s, t)
PY"

# TC-10 (regression): schema 없는 v2는 main()이 검증 없이 통과시킨다(코드 경로 확인)
chk "TC-10 v2 무검증 경로" "grep -q 'if summary.get(\"schema\") == \"v3\":' scripts/save_summary.py"

echo "PASS=$PASS FAIL=$FAIL"; [ "$FAIL" -eq 0 ]

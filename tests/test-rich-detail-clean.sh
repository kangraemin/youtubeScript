#!/bin/bash
# 상세 요약(detail) 정리 규칙: 빈말 제거, 길이·개수 상한, 숫자 없는 가격 제거, best 메뉴 먼저
set -e
cd "$(dirname "$0")/.."
.venv/bin/python - <<'PY'
import sys
sys.path[:0] = ["worker", "."]
from restaurant_extractor import clean_detail, EXTRACT_PROMPT, PROMPT_VERSION
assert PROMPT_VERSION.startswith("v4"), PROMPT_VERSION
assert "해요체" in EXTRACT_PROMPT and "~라는 평" in EXTRACT_PROMPT
assert '"detail"' in EXTRACT_PROMPT
d = clean_detail({
    "recommend": "강추", "verdict": "가" * 60, "price": "비싸다고 함", "parking": "언급 없음",
    "pros": ["a", "b", "c", "d", "e"], "cons": [], "tips": ["", "팁"],
    "dishes": [{"name": "소불고기", "comment": "맛있다", "best": False, "ts": "10:50"},
               {"name": "한우불고기", "comment": "최고", "best": True, "ts": "03:22"}, {"comment": "이름 없음"}],
})
assert d["recommend"] == "강추"
assert len(d["verdict"]) == 40 and d["verdict"].endswith("…")
assert "price" not in d and "parking" not in d and "cons" not in d
assert d["pros"] == ["a", "b", "c", "d"] and d["tips"] == ["팁"]
assert [x["name"] for x in d["dishes"]] == ["한우불고기", "소불고기"] and d["dishes"][0]["ts"] == "03:22"
assert clean_detail({"recommend": "최고", "verdict": "없음"}) is None
assert clean_detail("x") is None
print("PASS")
PY

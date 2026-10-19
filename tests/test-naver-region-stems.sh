#!/bin/bash
# 시·군 단위 힌트(고흥·단양)가 주소 행정구역과 맞으면 지역 점수가 오르는지 본다
cd "$(dirname "$0")/.." || exit 1
.venv/bin/python - <<'PY'
from worker.naver_search import _pick_best, _hint_regions, _admin_stems
assert _admin_stems("충청북도 단양군 가곡면 대대길 27-2") == ["단양", "가곡"]
assert _admin_stems("전남광주통합특별시 고흥군 도덕면") == ["고흥", "도덕"]
assert _admin_stems("서울특별시 중구 퇴계로") == []
a = {"roadAddress": "서울특별시 중구 퇴계로50길 37", "title": "태화루"}
b = {"roadAddress": "전남광주통합특별시 고흥군 고흥읍 시장길 1", "title": "태화루"}
hint = "고흥 전통시장"
it, sc = _pick_best([a, b], _hint_regions(hint), hint)
assert it is b and sc >= 1, (it, sc)
# 힌트에 맞는 후보가 없으면: 키워드가 없던 힌트는 첫 결과를 점수 0으로 (기존 동작)
it, sc = _pick_best([a], _hint_regions(hint), hint)
assert it is a and sc == 0, (it, sc)
# 키워드 힌트("광주")가 있는데 전부 불일치면 None
it, sc = _pick_best([a], _hint_regions("광주"), "광주")
assert it is None
# 힌트 없음 → 첫 결과, 점수 0
assert _pick_best([a, b], [], "") == (a, 0)
print("PASS test-naver-region-stems")
PY

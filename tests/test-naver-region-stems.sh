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
from worker.naver_search import name_close, _hint_has_street
assert name_close("청석골 칙냉면", "청석골칡냉면")
assert name_close("데일리브루커피로스터스", "데일리브루커피앤로스터스")
assert not name_close("삼명식당", "삼명푸드")
assert not name_close("노케찹", "바르미심비디움 NC이스트폴구의점")
assert _hint_has_street("서울 중구 필동3가 서애로1길 6-4, 충무로역 근처", "서울특별시 중구 서애로1길 6-4")
assert not _hint_has_street("통영 중앙시장", "경상남도 통영시 새터길 12-10")
from worker.naver_search import _confident
# 철자만 비슷 + 힌트 구(광진구)가 주소에 없음 → low
assert not _confident("거북이삼겹살", "거북이네김치생삼겹살", "서울특별시 중구 퇴계로37길 24", ["서울", "광진구"], "서울 광진구 중곡1동 241-30", 1)
# 철자만 비슷 + 힌트 도로명이 주소와 다름 → low
assert not _confident("해운대밀면", "해운대 가야밀면", "부산광역시 해운대구 좌동순환로 27", ["부산", "해운대"], "부산 해운대구 중동2로 10번길 21", 2)
assert _confident("청석골 칙냉면", "청석골칡냉면", "전남광주통합특별시 광산구 산월로3번길 46 2층", ["광주"], "광주 광산구 첨단 쌍암공원 근처", 1)
print("PASS test-naver-region-stems")
PY

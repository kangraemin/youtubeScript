#!/bin/bash
# 같은 이름의 다른 지점·다른 업종이 high로 붙지 않는지 본다(나이쏘이 강남점↔하비오점, 바찌 셔츠 가게)
cd "$(dirname "$0")/.." || exit 1
.venv/bin/python - <<'PY'
from worker.naver_search import _confident, _pick_best, _hint_regions, _hint_districts
# 구가 다르면 이름이 같아도 low
assert not _confident("나이쏘이", "나이쏘이 하비오점", "서울특별시 송파구 송파대로 111", ["서울", "강남구"], "서울 강남구 역삼동", 1)
# 구가 맞으면 high
assert _confident("나이쏘이", "나이쏘이 강남점", "서울특별시 강남구 테헤란로 1", ["서울", "강남구"], "서울 강남구 역삼동", 2)
# 지점명이 다르면 low
assert not _confident("나이쏘이 강남점", "나이쏘이 하비오점", "서울특별시 송파구 송파대로 111", ["서울"], "서울", 1)
# 광역시 이름은 구로 치지 않는다
assert _hint_districts("대구 중구 동성로") == ["중구"]
assert _hint_districts("서울시 마포구") == ["마포구"]
assert _confident("로기", "로기", "대구광역시 중구 동성로 1", ["대구"], "대구 중구", 1)
# 옷가게는 후보에서 빠진다
shirt = {"roadAddress": "서울특별시 송파구 오금로 1", "title": "바찌", "category": "쇼핑,유통>의류"}
pizza = {"roadAddress": "서울특별시 성동구 연무장길 1", "title": "바찌서울", "category": "음식점>양식"}
it, _ = _pick_best([shirt, pizza], _hint_regions("서울"), "서울")
assert it is pizza, it
it, _ = _pick_best([shirt], _hint_regions("서울"), "서울")
assert it is None
print("PASS test-naver-wrong-branch")
PY

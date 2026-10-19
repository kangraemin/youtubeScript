#!/usr/bin/env bash
# 맛집 채널: 모아보기·몰아보기 편집본과 2시간 넘는 영상은 수집·가공에서 뺀다
set -euo pipefail
cd "$(dirname "$0")/.."
PY=.venv/bin/python
$PY - <<'PY'
from scripts.channel_config import is_compilation, policy_for
assert is_compilation("광주 59박 60일 몰아보기", 600)
assert is_compilation("부산 맛집 모아보기", 900)
assert is_compilation("600만 기념 6시간 라이브", 6 * 3600)
assert not is_compilation("국밥 먹방", 1200)
assert not is_compilation("2시간 딱 맞는 영상", 7200)
assert not is_compilation("길이 모름", -1)
assert policy_for("tzuyang").get("skip_compilations")
assert not policy_for("moneycomics").get("skip_compilations")
print("OK is_compilation")
PY
grep -q 'is_compilation' scripts/crawl_youtube_transcripts.py
grep -q 'is_compilation' worker/pipeline.py
echo "PASS test-skip-food-compilations"

#!/usr/bin/env bash
# E2E: 크롤러 transcript 중복 제거 + DB 정리 스크립트
# 실행: bash tests/test-transcript-dedup.sh
set -euo pipefail
cd "$(git rev-parse --show-toplevel)"
FAIL=0

echo "### TC1: dedup_segments 순수함수 — 2배/3배/정상/빈입력"
python3 - <<'PY' || FAIL=1
import sys; sys.path.insert(0, '.')
from scripts.crawl_youtube_transcripts import dedup_segments, _ts_to_seconds

assert _ts_to_seconds("1:23") == 83
assert _ts_to_seconds("1:02:03") == 3723
assert _ts_to_seconds("garbage") is None

base = [{"timestamp": f"{m}:{s:02d}", "text": f"t{m}{s}"}
        for m in range(3) for s in (0, 30)]   # 6 seg, 0:00..2:30 단조
assert dedup_segments(base) == base, "정상 입력 변형됨"
assert dedup_segments(base + base) == base, "2배 미제거"
assert dedup_segments(base + base + base) == base, "3배 미제거"
assert dedup_segments([]) == []
assert dedup_segments(base[:1]) == base[:1]
print("✅ dedup_segments: 2x/3x→1x, 정상·빈·단일 무변경")
PY

echo "### TC2: dedup_text (DB 텍스트) — header 보존·1사이클·idempotent"
python3 - <<'PY' || FAIL=1
import sys; sys.path.insert(0, '.')
from scripts.dedupe_transcripts import dedup_text

header = "제목\nhttps://x\nvideo_id: ABC\ncollected_at: 2026-05-19T00:00:00\n"
body = "0:00 안녕\n0:30 본문\n1:00 끝"
clean = header + body
dup = header + body + "\n" + body          # 2배 (타임스탬프 0:00 역행)

new, ch = dedup_text(dup)
assert ch is True and new == clean.rstrip(), f"중복 미정리: {new!r}"
n2, c2 = dedup_text(new)
assert c2 is False and n2 == new, "idempotent 위반(2회차 변경)"
n3, c3 = dedup_text(clean)
assert c3 is False and n3 == clean, "정상 텍스트 변형됨(데이터 손실 위험)"
assert new.startswith("제목\nhttps://x\nvideo_id: ABC"), "header 손상"
print("✅ dedup_text: 중복 절단·header 보존·idempotent·무손실")
PY

echo "### TC3: get_transcript가 return 전 dedup_segments 적용"
grep -q 'return dedup_segments(result) or None' scripts/crawl_youtube_transcripts.py \
  && echo "✅ get_transcript dedup 적용" || { echo "❌ dedup 미적용"; FAIL=1; }

echo "### TC4: dedupe_transcripts.py dry-run 실행 (DB 무변경 보장)"
python3 -m py_compile scripts/crawl_youtube_transcripts.py scripts/dedupe_transcripts.py \
  && echo "✅ py_compile" || { echo "❌ compile"; FAIL=1; }
python3 scripts/dedupe_transcripts.py --limit 1000 | tail -1 | grep -q 'DRY-RUN' \
  && echo "✅ dry-run 정상 실행 (apply 없이 보고만)" || { echo "❌ dry-run 실패"; FAIL=1; }

echo "### TC5: 기존 크롤 회귀"
bash tests/test-crawl-cutoff-shorts-filter.sh >/dev/null 2>&1 \
  && echo "✅ crawl-cutoff-shorts 회귀 통과" || { echo "❌ 회귀 실패"; FAIL=1; }

echo "---"
[ "$FAIL" -eq 0 ] && echo "✅ E2E ALL PASS" || { echo "❌ E2E FAIL"; exit 1; }

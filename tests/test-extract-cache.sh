#!/bin/bash
# 추출 결과를 로컬에 먼저 남기고, 다시 돌면 claude를 또 부르지 않는다(DB가 죽어 회차가 끊겨도 재추출 안 함)
set -e
cd "$(dirname "$0")/.."
TMP=$(mktemp -d)
trap 'rm -rf "$TMP"' EXIT
.venv/bin/python - "$TMP" <<'PY'
import sys
from pathlib import Path
sys.path.insert(0, "worker")
import pipeline as p
p.EXTRACT_DIR = Path(sys.argv[1]) / "extract"
p.USAGE_LOG = Path(sys.argv[1]) / "usage.jsonl"
calls = []
def fake_extract(t, title="", description=""):
    calls.append(1)
    return [], {"input_tokens": 1, "output_tokens": 1}
p.extract_restaurants = fake_extract
p.fetch_transcript = lambda vid: [{"start": 0, "text": "x"}]
stats = {k: 0 for k in ["failed", "input_tokens", "output_tokens", "skipped", "naver_calls", "closed", "restaurants", "needs_review"]}
v = {"video_id": "TESTVID0001", "title": "t", "channel_id": "c"}
p.process_video(None, v, stats)
assert (p.EXTRACT_DIR / "TESTVID0001.json").exists(), "추출 결과 파일이 없다"
p.process_video(None, v, stats)
assert len(calls) == 1, f"두 번째에도 추출을 불렀다: {len(calls)}"
# 프롬프트 버전이 바뀌면 다시 뽑는다
p.PROMPT_VERSION = "other"
p.process_video(None, v, stats)
assert len(calls) == 2, "프롬프트 버전이 바뀌었는데 옛 결과를 썼다"
print("OK")
PY

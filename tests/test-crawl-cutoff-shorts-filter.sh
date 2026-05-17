#!/usr/bin/env bash
# E2E: cutoff 조기 return 경로에서도 쇼츠 필터가 적용되는지 검증
# 실행: bash tests/test-crawl-cutoff-shorts-filter.sh
set -euo pipefail
cd "$(git rev-parse --show-toplevel)"
FAIL=0

echo "### TC1: 구조 — 조기 return이 필터를 우회하지 않음"
if grep -nE '^[[:space:]]+return videos[[:space:]]*$' scripts/crawl_youtube_transcripts.py; then
  echo "❌ bare 'return videos' 잔존 — 필터 우회 경로 존재"; FAIL=1
else
  echo "✅ bare 'return videos' 없음"
fi
grep -q 'def _finalize' scripts/crawl_youtube_transcripts.py && echo "✅ _finalize helper 존재" || { echo "❌ _finalize 없음"; FAIL=1; }

echo "### TC2: 기능 — cutoff 조기 return 시 쇼츠 제외"
python3 - <<'PY' || FAIL=1
import sys; sys.path.insert(0, '.')
from datetime import datetime, timezone, timedelta
from scripts import crawl_youtube_transcripts as M

now = datetime.now(timezone.utc)
recent = (now - timedelta(days=2)).isoformat().replace('+00:00','Z')
old    = (now - timedelta(days=90)).isoformat().replace('+00:00','Z')

PAGE = {"items": [
    {"snippet": {"resourceId": {"videoId": "LONG1"}, "title": "long",  "publishedAt": recent}},
    {"snippet": {"resourceId": {"videoId": "SHORT1"},"title": "short", "publishedAt": recent}},
    {"snippet": {"resourceId": {"videoId": "OLDV"},  "title": "old",   "publishedAt": old}},
]}
DUR = {"items": [
    {"id": "LONG1",  "contentDetails": {"duration": "PT10M"}},   # 600s keep
    {"id": "SHORT1", "contentDetails": {"duration": "PT45S"}},   # 45s  drop
]}

class _Req:
    def __init__(self, data): self._d = data
    def execute(self): return self._d
class _PlaylistItems:
    def list(self, **k): return _Req(PAGE)
    def list_next(self, req, resp): return None
class _Videos:
    def list(self, **k): return _Req(DUR)
class _YT:
    def playlistItems(self): return _PlaylistItems()
    def videos(self): return _Videos()

ch = {"id": "UC_test_channelid_xxxx", "slug": "yonhap_economy", "name": "T", "tab": "videos"}
res = M.get_channel_videos_api(_YT(), ch, max_videos=0, days_limit=30)
vids = [v["vid"] for v in res]
assert "LONG1" in vids, f"긴영상 누락: {vids}"
assert "SHORT1" not in vids, f"쇼츠가 필터 안 됨(버그): {vids}"
assert "OLDV" not in vids, f"cutoff 초과 영상 포함: {vids}"
print(f"✅ cutoff 조기 return 경로에서 쇼츠 제외 확인 (결과={vids})")
PY

echo "### TC3: py_compile"
python3 -m py_compile scripts/crawl_youtube_transcripts.py && echo "✅ compile" || FAIL=1

echo "---"
[ "$FAIL" -eq 0 ] && echo "✅ E2E ALL PASS" || { echo "❌ E2E FAIL"; exit 1; }

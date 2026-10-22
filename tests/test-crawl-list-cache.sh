#!/usr/bin/env bash
# E2E: 긴 기간 채널 목록은 24시간 캐시로 재사용해 YouTube API quota를 아끼는지 검증
# 실행: bash tests/test-crawl-list-cache.sh
set -euo pipefail
cd "$(git rev-parse --show-toplevel)"
FAIL=0
TMP=$(mktemp -d)
trap 'rm -rf "$TMP"' EXIT

echo "### TC1: 긴 기간은 두 번째 호출에서 API를 안 부르고, 짧은 기간·만료 캐시는 다시 부른다"
CACHE_DIR="$TMP" .venv/bin/python - <<'PY' || FAIL=1
import os, sys, time; sys.path.insert(0, '.')
from datetime import datetime, timezone, timedelta
from pathlib import Path
from scripts import crawl_youtube_transcripts as M

M.LIST_CACHE_DIR = Path(os.environ["CACHE_DIR"])
recent = (datetime.now(timezone.utc) - timedelta(days=2)).isoformat().replace('+00:00', 'Z')
PAGE = {"items": [{"snippet": {"resourceId": {"videoId": "V1"}, "title": "t", "publishedAt": recent}}]}
DUR = {"items": [{"id": "V1", "contentDetails": {"duration": "PT10M"}}]}
calls = {"n": 0}

class _Req:
    def __init__(self, d): self._d = d
    def execute(self):
        calls["n"] += 1
        return self._d
class _PlaylistItems:
    def list(self, **k): return _Req(PAGE)
    def list_next(self, req, resp): return None
class _Videos:
    def list(self, **k): return _Req(DUR)
class _YT:
    def playlistItems(self): return _PlaylistItems()
    def videos(self): return _Videos()

ch = {"id": "UC_test_channelid_xxxx", "slug": "tzuyang", "name": "T", "tab": "videos"}

first = M.get_channel_videos_api(_YT(), ch, 0, 2190)
n1 = calls["n"]
assert n1 > 0 and [v["vid"] for v in first] == ["V1"], (n1, first)
second = M.get_channel_videos_api(_YT(), ch, 0, 2190)
assert calls["n"] == n1, f"캐시가 있는데 API를 다시 불렀다: {calls['n']} vs {n1}"
assert second == first, (second, first)
print("✅ 긴 기간 두 번째 호출은 캐시 사용")

M.get_channel_videos_api(_YT(), ch, 0, 30)
assert calls["n"] > n1, "짧은 기간 정기 크롤은 캐시를 쓰면 안 된다(새 영상 누락)"
print("✅ 짧은 기간은 매번 API 호출")

n2 = calls["n"]
path = next(M.LIST_CACHE_DIR.glob("tzuyang_*.json"))
old = time.time() - M.LIST_CACHE_TTL_SEC - 10
os.utime(path, (old, old))
M.get_channel_videos_api(_YT(), ch, 0, 2190)
assert calls["n"] > n2, "24시간 지난 캐시는 다시 받아야 한다"
print("✅ 만료된 캐시는 다시 받음")
PY

echo "### TC2: py_compile"
.venv/bin/python -m py_compile scripts/crawl_youtube_transcripts.py && echo "✅ compile" || FAIL=1

echo "---"
[ "$FAIL" -eq 0 ] && echo "ALL PASS" || { echo "FAIL"; exit 1; }

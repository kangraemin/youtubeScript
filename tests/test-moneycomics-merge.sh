#!/usr/bin/env bash
# E2E: 머니코믹스 슬러그 단일화 검증
# 실행: bash tests/test-moneycomics-merge.sh
set -euo pipefail
cd "$(git rev-parse --show-toplevel)"
FAIL=0

echo "### TC1: 코드에서 moneycomics_videos 완전 제거"
if grep -rn 'moneycomics_videos' scripts/channel_config.py scripts/crawl_youtube_transcripts.py web/lib/channels.ts; then
  echo "❌ moneycomics_videos 잔존"; FAIL=1
else echo "✅ 코드 3파일에서 제거됨"; fi

echo "### TC2: channel_config 정책 — moneycomics summary=True"
.venv/bin/python - <<'PY' || FAIL=1
import sys; sys.path.insert(0,'.')
from scripts.channel_config import STOCK_ECON_SLUGS, SUMMARY_SLUGS, policy_for
assert "moneycomics" in STOCK_ECON_SLUGS, "moneycomics not in STOCK_ECON"
assert "moneycomics_videos" not in STOCK_ECON_SLUGS, "videos 잔존"
assert "moneycomics" in SUMMARY_SLUGS
assert policy_for("moneycomics")["summary"] is True
print("✅ moneycomics summary=True 정책 OK")
PY

echo "### TC3: 크롤러 CHANNELS slug=moneycomics (id 보존)"
.venv/bin/python - <<'PY' || FAIL=1
import sys; sys.path.insert(0,'.')
from scripts.crawl_youtube_transcripts import CHANNELS
m=[c for c in CHANNELS if c["id"]=="UCJo6G1u0e_-wS-JQn3T-zEw"]
assert len(m)==1 and m[0]["slug"]=="moneycomics", m
assert not any(c["slug"]=="moneycomics_videos" for c in CHANNELS)
print("✅ 크롤러 단일 moneycomics 엔트리")
PY

echo "### TC4: DB — moneycomics_videos 0행, moneycomics 통합"
.venv/bin/python - <<'PY' || FAIL=1
import sys; sys.path.insert(0,'.')
from worker.supabase_client import get_client
db=get_client()
v=db.table("transcripts").select("vid",count="exact",head=True).eq("channel_slug","moneycomics_videos").execute().count
m=db.table("transcripts").select("vid",count="exact",head=True).eq("channel_slug","moneycomics").execute().count
assert v==0, f"moneycomics_videos 잔존 {v}행"
assert m>=499, f"moneycomics {m}행 (>=499 기대)"
print(f"✅ DB 통합: moneycomics_videos=0, moneycomics={m}")
PY

echo "### TC5: rawdata 디렉토리 단일화"
[ ! -d rawdata/transcripts/moneycomics_videos ] && echo "✅ moneycomics_videos 디렉토리 없음" || { echo "❌ 디렉토리 잔존"; FAIL=1; }
[ -d rawdata/transcripts/moneycomics ] && echo "✅ moneycomics 디렉토리 존재" || { echo "❌ moneycomics 디렉토리 없음"; FAIL=1; }

echo "### TC6: py_compile + 회귀"
.venv/bin/python -m py_compile scripts/channel_config.py scripts/crawl_youtube_transcripts.py && echo "✅ compile" || FAIL=1
bash tests/test-yonhap-shorts-exclude.sh >/dev/null 2>&1 && echo "✅ yonhap 회귀" || { echo "❌ yonhap 회귀 깨짐"; FAIL=1; }

echo "---"
[ "$FAIL" -eq 0 ] && echo "✅ E2E ALL PASS" || { echo "❌ E2E FAIL"; exit 1; }

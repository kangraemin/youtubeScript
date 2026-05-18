#!/usr/bin/env bash
# E2E: fetchChannelStats 단일 쿼리 집계가 채널별 count='exact'와 동치 + 성능
# 실행: bash tests/test-channel-stats-single-query.sh
set -euo pipefail
cd "$(git rev-parse --show-toplevel)"
FAIL=0

echo "### TC1: 단일 쿼리 집계 == 채널별 count exact (동치)"
.venv/bin/python - <<'PY' || FAIL=1
import sys; sys.path.insert(0,'.')
from worker.supabase_client import get_client
db=get_client()
rows=[];frm=0
while True:
    r=db.table("transcripts").select("channel_slug,published_at").not_.is_("summary","null").range(frm,frm+999).execute()
    d=r.data or []; rows+=d
    if len(d)<1000: break
    frm+=1000
from collections import defaultdict
new_cnt=defaultdict(int); new_latest={}
for x in rows:
    c=x["channel_slug"]; new_cnt[c]+=1
    p=x["published_at"]
    if p and (c not in new_latest or p>new_latest[c]): new_latest[c]=p
for c in list(new_cnt):
    cexact=db.table("transcripts").select("vid",count="exact",head=True).eq("channel_slug",c).not_.is_("summary","null").execute().count
    assert cexact==new_cnt[c], f"{c}: 단일집계 {new_cnt[c]} != count exact {cexact}"
print(f"✅ {len(new_cnt)}개 채널 집계 동치 (count 일치)")
PY

echo "### TC2: 단일 쿼리가 채널별-루프보다 빠름 (성능)"
.venv/bin/python - <<'PY' || FAIL=1
import sys,time; sys.path.insert(0,'.')
from worker.supabase_client import get_client
db=get_client()
s=time.time()
rows=[];frm=0
while True:
    r=db.table("transcripts").select("channel_slug,published_at").not_.is_("summary","null").range(frm,frm+999).execute()
    d=r.data or []; rows+=d
    if len(d)<1000: break
    frm+=1000
single=time.time()-s
chans=sorted({x["channel_slug"] for x in rows})
s=time.time()
for c in chans:
    db.table("transcripts").select("vid",count="exact",head=True).eq("channel_slug",c).not_.is_("summary","null").execute()
    db.table("transcripts").select("published_at").eq("channel_slug",c).order("published_at",desc=True).limit(1).execute()
multi=time.time()-s
print(f"단일 {single:.2f}s vs 채널별 {multi:.2f}s ({len(chans)}채널)")
assert single < multi, f"단일({single:.2f}) >= 멀티({multi:.2f}) — 성능 이득 없음"
assert single < 2.0, f"단일 {single:.2f}s > 2s (너무 느림)"
print(f"✅ 단일 쿼리 {single:.2f}s, 멀티 대비 빠름")
PY

echo "### TC3: page.tsx 구조 — 단일 쿼리 패턴 적용 + 시그니처 보존"
grep -q "count: 'exact'" web/app/page.tsx && { echo "❌ count:exact 잔존(채널별 루프)"; FAIL=1; } || echo "✅ count:exact 제거됨"
grep -q "async function fetchChannelStats(): Promise<ChannelStat\[\]>" web/app/page.tsx && echo "✅ 시그니처 보존" || { echo "❌ 시그니처 변경됨"; FAIL=1; }
grep -q "STOCK_ECON_SLUGS.map" web/app/page.tsx && echo "✅ STOCK_ECON_SLUGS 순서 유지 매핑" || { echo "❌ 채널 순서 매핑 없음"; FAIL=1; }

echo "### TC4: web 타입체크"
( cd web && npx --yes tsc --noEmit -p tsconfig.json ) && echo "✅ tsc 무오류" || { echo "❌ tsc 오류"; FAIL=1; }

echo "---"
[ "$FAIL" -eq 0 ] && echo "✅ E2E ALL PASS" || { echo "❌ E2E FAIL"; exit 1; }

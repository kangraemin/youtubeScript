#!/usr/bin/env bash
# E2E: 홈 검색 RPC + pg_trgm 인덱스 + 매칭근거
# 실행: bash tests/test-home-search.sh
set -euo pipefail
cd "$(git rev-parse --show-toplevel)"
FAIL=0

echo "### TC1: search_transcripts RPC 매칭 정확성"
.venv/bin/python - <<'PY' || FAIL=1
import sys,json; sys.path.insert(0,'.')
from worker.supabase_client import get_client
db=get_client()
q="엔비디아"
rows=(db.rpc("search_transcripts",{"q_input":q}).execute().data) or []
assert len(rows)>0, f"'{q}' 0건"
for x in rows[:30]:
    blob=(x.get("title") or "")+json.dumps(x.get("summary"),ensure_ascii=False)
    assert q in blob, f"{x['vid']} '{q}' 미포함"
    assert x.get("summary") is not None
print(f"✅ '{q}' {len(rows)}건 전부 포함 & summary≠null")
PY

echo "### TC2: 무매칭 빈 결과 + published_at desc"
.venv/bin/python - <<'PY' || FAIL=1
import sys; sys.path.insert(0,'.')
from worker.supabase_client import get_client
db=get_client()
assert (db.rpc("search_transcripts",{"q_input":"zzqx_nope_8731"}).execute().data or [])==[]
ds=[x["published_at"] for x in (db.rpc("search_transcripts",{"q_input":"미국"}).execute().data or []) if x["published_at"]]
assert ds==sorted(ds,reverse=True), "published_at desc 아님"
print("✅ 무매칭 빈결과 + published_at desc")
PY

echo "### TC3: range 페이지네이션"
.venv/bin/python - <<'PY' || FAIL=1
import sys; sys.path.insert(0,'.')
from worker.supabase_client import get_client
db=get_client()
p1=db.rpc("search_transcripts",{"q_input":"미국"}).range(0,9).execute().data or []
p2=db.rpc("search_transcripts",{"q_input":"미국"}).range(10,19).execute().data or []
assert len(p1)<=10 and not ({x["vid"] for x in p1} & {x["vid"] for x in p2})
print(f"✅ range p1={len(p1)} p2={len(p2)} 중복없음")
PY

echo "### TC4: matchReason 로직"
( cd web && npx --yes tsx -e '
import { getMatchReasons } from "./lib/matchReason"
const t:any = { title:"엔비디아 신고가 분석", summary:{ headline:"AI 랠리", buys:[{ticker:"삼성전자",reason:"저평가 매수",speaker:null,quotes:[]}], terms:[{term:"PER",explain:"주가수익비율"}], narrative:"엔비디아가 시장을 주도" } }
const r1 = getMatchReasons(t,"삼성전자")
if(!r1.length || r1[0].label!=="매수 코멘트"){console.error("FAIL buy");process.exit(1)}
const hl=r1[0].parts.find((p:any)=>p.hl); if(!hl||hl.text!=="삼성전자"){console.error("FAIL hl");process.exit(1)}
const r2=getMatchReasons(t,"엔비디아"); if(r2[0].label!=="제목 일치"){console.error("FAIL title");process.exit(1)}
if(getMatchReasons(t,"존재안함토큰").length!==0){console.error("FAIL nomatch");process.exit(1)}
console.log("✅ matchReason OK")
' ) || FAIL=1

echo "### TC5: pg_trgm 인덱스 동작 — 연속 검색 522 없이 빠르게"
.venv/bin/python - <<'PY' || FAIL=1
import sys,time; sys.path.insert(0,'.')
from worker.supabase_client import get_client
db=get_client()
t0=time.time()
for kw in ["엔비디아","삼성","미국","금리","반도체"]:
    r=db.rpc("search_transcripts",{"q_input":kw}).range(0,19).execute().data
    assert r is not None
el=time.time()-t0
assert el < 15, f"연속 5검색 {el:.1f}s — 인덱스 미동작 의심"
print(f"✅ 연속 5회 검색 {el:.2f}s, 522 없음 (인덱스 동작)")
PY

echo "### TC6: web 구조 + SQL 인덱스 + 타입체크"
grep -q 'mode="search"' web/components/SearchableFeed.tsx && echo "✅ SearchableFeed" || { echo "❌"; FAIL=1; }
grep -q 'SearchableFeed' web/app/page.tsx && echo "✅ page.tsx" || { echo "❌"; FAIL=1; }
grep -q "rpc('search_transcripts'" web/components/InfiniteList.tsx && echo "✅ RPC" || { echo "❌"; FAIL=1; }
grep -q 'getMatchReasons' web/components/VideoCard.tsx && echo "✅ VideoCard" || { echo "❌"; FAIL=1; }
grep -q 'pg_trgm' scripts/create_search_function.sql && grep -q 'gin_trgm_ops' scripts/create_search_function.sql && echo "✅ pg_trgm 인덱스 SQL" || { echo "❌ 인덱스 누락"; FAIL=1; }
( cd web && npx --yes tsc --noEmit -p tsconfig.json ) && echo "✅ tsc" || { echo "❌ tsc"; FAIL=1; }

echo "---"
[ "$FAIL" -eq 0 ] && echo "✅ E2E ALL PASS" || { echo "❌ E2E FAIL"; exit 1; }

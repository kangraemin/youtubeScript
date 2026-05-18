#!/usr/bin/env bash
# E2E: 웹 3종 (뒤로가기 캐시 / ISR+무효화 / 검색 최적화)
# 실행: bash tests/test-web-perf-3in1.sh
set -euo pipefail
cd "$(git rev-parse --show-toplevel)"
FAIL=0

echo "### TC1: search RPC가 transcript 컬럼 미반환 (최적화)"
.venv/bin/python - <<'PY' || FAIL=1
import sys; sys.path.insert(0,'.')
from worker.supabase_client import get_client
db=get_client()
rows=db.rpc("search_transcripts",{"q_input":"엔비디아"}).execute().data or []
assert len(rows)>0
keys=set(rows[0].keys())
assert "transcript" not in keys, f"transcript 잔존: {keys}"
assert {"vid","title","summary","published_at"} <= keys, f"필수컬럼 누락: {keys}"
print(f"✅ {len(rows)}건, 컬럼={sorted(keys)} (transcript 제외)")
PY

echo "### TC2: search 정확성·무매칭·정렬 회귀"
.venv/bin/python - <<'PY' || FAIL=1
import sys,json; sys.path.insert(0,'.')
from worker.supabase_client import get_client
db=get_client()
r=db.rpc("search_transcripts",{"q_input":"엔비디아"}).execute().data or []
for x in r[:20]:
    assert "엔비디아" in (x.get("title") or "")+json.dumps(x.get("summary"),ensure_ascii=False)
assert (db.rpc("search_transcripts",{"q_input":"zzqx_nope_8731"}).execute().data or [])==[]
ds=[x["published_at"] for x in r if x["published_at"]]
assert ds==sorted(ds,reverse=True)
print("✅ 정확성·무매칭·published_at desc 유지")
PY

echo "### TC3: SearchableFeed 최소길이 2 가드"
grep -q 'length >= 2' web/components/SearchableFeed.tsx && echo "✅ min-length 2 가드" || { echo "❌"; FAIL=1; }

echo "### TC4: ISR 3600 + revalidate route"
grep -q 'revalidate = 3600' web/app/page.tsx && grep -q 'revalidate = 3600' web/app/latest/page.tsx && echo "✅ revalidate 3600 (page+latest)" || { echo "❌ revalidate 미변경"; FAIL=1; }
test -f web/app/api/revalidate/route.ts && grep -q 'revalidatePath' web/app/api/revalidate/route.ts && grep -q 'REVALIDATE_SECRET' web/app/api/revalidate/route.ts && echo "✅ revalidate route + 토큰검증" || { echo "❌ route 없음/불완전"; FAIL=1; }

echo "### TC5: save_summary revalidate 호출 (저장 실패 무관)"
grep -q '/api/revalidate' scripts/save_summary.py && grep -q 'revalidate skip' scripts/save_summary.py && echo "✅ save_summary revalidate 훅(예외무시)" || { echo "❌"; FAIL=1; }
.venv/bin/python -m py_compile scripts/save_summary.py && echo "✅ save_summary compile" || FAIL=1

echo "### TC6: InfiniteList sessionStorage 복원 로직"
grep -q "sessionStorage.getItem(storageKey)" web/components/InfiniteList.tsx && \
grep -q "sessionStorage.setItem(" web/components/InfiniteList.tsx && \
grep -q "window.scrollTo(0, c.scrollY" web/components/InfiniteList.tsx && echo "✅ 저장/복원/스크롤복원" || { echo "❌ sessionStorage 로직 누락"; FAIL=1; }

echo "### TC7: web 타입체크 + 기존 회귀"
( cd web && npx --yes tsc --noEmit -p tsconfig.json ) && echo "✅ tsc" || { echo "❌ tsc"; FAIL=1; }
bash tests/test-home-search.sh >/dev/null 2>&1 && echo "✅ home-search 회귀" || { echo "❌ home-search 회귀"; FAIL=1; }
bash tests/test-feed-sort-published.sh >/dev/null 2>&1 && echo "✅ feed-sort 회귀" || { echo "❌ feed-sort 회귀"; FAIL=1; }
bash tests/test-channel-stats-single-query.sh >/dev/null 2>&1 && echo "✅ channel-stats 회귀" || { echo "❌ channel-stats 회귀"; FAIL=1; }

echo "---"
[ "$FAIL" -eq 0 ] && echo "✅ E2E ALL PASS" || { echo "❌ E2E FAIL"; exit 1; }

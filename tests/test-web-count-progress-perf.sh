#!/bin/bash
# tests/test-web-count-progress-perf.sh
# 홈 카운트 0 버그 + 화면이동 progress + 브라우즈 피드 경량화 검증
set -e
cd "$(dirname "$0")/.."
PASS=0; FAIL=0
chk(){ if eval "$2"; then echo "✅ $1"; PASS=$((PASS+1)); else echo "❌ $1"; FAIL=$((FAIL+1)); fi; }

# TC-1 (type-check): web tsc 통과
chk "TC-1 web tsc" "(cd web && npx tsc --noEmit)"

# TC-2 (negative): page.tsx가 에러 시 throw (0 캐시 방지)
chk "TC-2 fetchChannelStats throw" "grep -q 'throw error' web/app/page.tsx"

# TC-3 (happy): loading.tsx 4종 + RouteProgress + layout 마운트
chk "TC-3 progress 파일/마운트" "[ -f web/app/loading.tsx ] && [ -f 'web/app/video/[vid]/loading.tsx' ] && [ -f 'web/app/channel/[slug]/loading.tsx' ] && [ -f web/app/latest/loading.tsx ] && [ -f web/components/RouteProgress.tsx ] && grep -q RouteProgress web/app/layout.tsx"

# TC-4 (integration): feed_summaries RPC가 headline+카운트만 반환(summary 본문 미포함)
chk "TC-4 feed RPC 경량" ".venv/bin/python -c \"
import scripts.get_next_unsummarized as g
r=g.run_sql('select * from public.feed_summaries(null,3,0)')
assert r, 'RPC 결과 없음'
keys=set(r[0].keys())
assert 'headline' in keys and 'n_buys' in keys and 'summary' not in keys, keys
print('feed_summaries keys', sorted(keys))\""

# TC-5 (regression): InfiniteList 브라우즈 모드가 feed_summaries RPC 사용
chk "TC-5 피드 RPC 전환" "grep -q 'feed_summaries' web/components/InfiniteList.tsx"

# TC-6 (regression): VideoCard + 타입이 경량필드(n_buys) 지원
chk "TC-6 VideoCard 양립" "grep -q 'n_buys' web/components/VideoCard.tsx && grep -q 'n_buys' web/lib/supabase.ts"

# TC-7 (integration): DB 요약수 >0 (데이터 정상, 0은 캐시 stale였음)
chk "TC-7 DB 요약수>0" ".venv/bin/python -c \"
from worker.supabase_client import get_client
n=get_client().table('transcripts').select('vid',count='exact',head=True).not_.is_('summary','null').execute().count
print('summarized', n); assert n>0\""

echo "PASS=$PASS FAIL=$FAIL"; [ "$FAIL" -eq 0 ]

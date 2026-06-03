#!/bin/bash
# tests/test-detail-progress-cache.sh
# 상세페이지 progress 즉시 표시(클릭 리스너) + 반복방문 캐시(revalidate 3600) 검증
set -e
cd "$(dirname "$0")/.."
PASS=0; FAIL=0
chk(){ if eval "$2"; then echo "✅ $1"; PASS=$((PASS+1)); else echo "❌ $1"; FAIL=$((FAIL+1)); fi; }

# TC-1 (type-check): web tsc 통과
chk "TC-1 web tsc" "(cd web && npx tsc --noEmit)"

# TC-2 (happy): RouteProgress가 capture 클릭 리스너로 즉시 시작
chk "TC-2 클릭 리스너" "grep -q \"addEventListener('click'\" web/components/RouteProgress.tsx"

# TC-3 (negative): 새탭/외부/download/수정클릭 가드 존재
chk "TC-3 네비 가드" "grep -q 'metaKey' web/components/RouteProgress.tsx && grep -q 'a.target' web/components/RouteProgress.tsx && grep -q 'download' web/components/RouteProgress.tsx && grep -q 'url.origin' web/components/RouteProgress.tsx"

# TC-4 (boundary): 동일경로 클릭은 start 안함(가드)
chk "TC-4 동일경로 가드" "grep -q 'window.location.pathname' web/components/RouteProgress.tsx"

# TC-5 (regression): 네비 완료(key 변화) 시 finish — usePathname 유지
chk "TC-5 finish 유지" "grep -q 'finish()' web/components/RouteProgress.tsx && grep -q 'usePathname' web/components/RouteProgress.tsx"

# TC-6 (happy): 상세 revalidate 3600
chk "TC-6 상세 revalidate" "grep -q 'revalidate = 3600' 'web/app/video/[vid]/page.tsx'"

# TC-7 (regression): RouteProgress 여전히 layout에 마운트
chk "TC-7 layout 마운트" "grep -q 'RouteProgress' web/app/layout.tsx"

echo "PASS=$PASS FAIL=$FAIL"; [ "$FAIL" -eq 0 ]

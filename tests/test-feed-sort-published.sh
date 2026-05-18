#!/usr/bin/env bash
# E2E: 최신요약 피드 정렬 = 영상 업로드시각(published_at) desc
# 실행: bash tests/test-feed-sort-published.sh
set -euo pipefail
cd "$(git rev-parse --show-toplevel)"
FAIL=0
F=web/components/InfiniteList.tsx

echo "### TC1: latest-summarized 블록이 published_at desc로 정렬"
BLOCK=$(awk "/mode === 'latest-summarized'/,/else if \(channelSlug\)/" "$F")
echo "$BLOCK" | grep -q "\.order('published_at', { ascending: false, nullsFirst: false })" \
  && echo "✅ published_at desc 적용" || { echo "❌ published_at 정렬 누락"; FAIL=1; }
echo "$BLOCK" | grep -q "\.order('summarized_at'" \
  && { echo "❌ summarized_at 정렬 잔존"; FAIL=1; } || echo "✅ summarized_at 정렬 제거됨"
echo "$BLOCK" | grep -q "\.not('summary', 'is', null)" \
  && echo "✅ 요약필터(summary not null) 유지" || { echo "❌ 요약필터 사라짐"; FAIL=1; }

echo "### TC2: channel-summarized 모드 회귀 — published_at desc 그대로"
grep -q "// channel-summarized — 요약된 영상만, published_at desc" "$F" \
  && echo "✅ channel 모드 주석 유지" || { echo "❌ channel 모드 변경됨"; FAIL=1; }
test "$(grep -c "\.order('published_at', { ascending: false, nullsFirst: false })" "$F")" = "2" \
  && echo "✅ published_at desc 2곳(latest+channel)" || { echo "❌ order 개수 불일치"; FAIL=1; }

echo "### TC3: 타입 체크 (tsc --noEmit 0 오류)"
( cd web && npx tsc --noEmit ) && echo "✅ tsc 통과" || { echo "❌ tsc 오류"; FAIL=1; }

echo "---"
[ "$FAIL" -eq 0 ] && echo "✅ E2E ALL PASS" || { echo "❌ E2E FAIL"; exit 1; }

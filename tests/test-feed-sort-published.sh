#!/usr/bin/env bash
# E2E: 최신요약 피드 정렬 = 영상 업로드시각(published_at) desc
# 피드는 /api/feed → lib/feed.ts → feed_summaries RPC(scripts/create_feed_function.sql)로 옮겨졌다.
# 실행: bash tests/test-feed-sort-published.sh
set -euo pipefail
cd "$(git rev-parse --show-toplevel)"
FAIL=0
SQL=scripts/create_feed_function.sql

echo "### TC1: feed_summaries가 published_at desc로 정렬"
grep -q "order by t.published_at desc nulls last" "$SQL" \
  && echo "✅ published_at desc 적용" || { echo "❌ published_at 정렬 누락"; FAIL=1; }
grep -qi "order by[^;]*summarized_at" "$SQL" \
  && { echo "❌ summarized_at 정렬 잔존"; FAIL=1; } || echo "✅ summarized_at 정렬 없음"
grep -q "t.summary is not null" "$SQL" \
  && echo "✅ 요약필터(summary not null) 유지" || { echo "❌ 요약필터 사라짐"; FAIL=1; }

echo "### TC2: 채널 모드도 같은 RPC(p_channel)로 같은 정렬"
grep -q "p_channel is null or t.channel_slug = p_channel" "$SQL" \
  && echo "✅ 채널 조건이 같은 쿼리 안에 있음" || { echo "❌ 채널 조건 변경됨"; FAIL=1; }
grep -q "rpc('feed_summaries'" web/lib/feed.ts && grep -q "p_channel: channel" web/lib/feed.ts \
  && echo "✅ 웹이 feed_summaries RPC 사용" || { echo "❌ 웹 피드 경로 변경됨"; FAIL=1; }

echo "### TC3: 타입 체크 (tsc --noEmit 0 오류)"
( cd web && npx tsc --noEmit ) && echo "✅ tsc 통과" || { echo "❌ tsc 오류"; FAIL=1; }

echo "---"
[ "$FAIL" -eq 0 ] && echo "✅ E2E ALL PASS" || { echo "❌ E2E FAIL"; exit 1; }

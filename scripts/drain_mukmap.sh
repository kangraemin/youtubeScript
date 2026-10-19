#!/bin/bash
# 쌓인 자막이 0개가 될 때까지 cron_mukmap.sh를 큰 회차로 반복한다(같은 락이라 정기 크론과 겹치지 않는다).
# 회차가 영상 0개를 처리했거나 막혔으면(blocked) 끝낸다.
cd /Users/ram/programming/vibecoding/youtubeScript
LOG="rawdata/reports/_mukmap.log"
for i in $(seq 1 "${DRAIN_MAX_ROUNDS:-100}"); do
  MUKMAP_MAX_VIDEOS="${DRAIN_BATCH:-100}" MUKMAP_MAX_MINUTES=55 bash scripts/cron_mukmap.sh
  last=$(grep '^{"videos"' "$LOG" | tail -1)
  echo "[drain $i] $last"
  case "$last" in
    *'"videos": 0,'*|*'"blocked"'*) echo "[drain] 종료: 남은 자막 없음 또는 막힘"; break ;;
  esac
done

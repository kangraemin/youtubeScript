#!/bin/bash
# 쌓인 자막이 0개가 될 때까지 cron_mukmap.sh를 큰 회차로 반복한다(같은 락이라 정기 크론과 겹치지 않는다).
# 회차가 영상 0개를 처리했거나 막혔으면(blocked) 끝낸다. 회차가 결과 줄 없이 죽으면 3번까지 다시 돈다.
cd /Users/ram/programming/vibecoding/youtubeScript
LOG="rawdata/reports/_mukmap.log"
# 이미 도는 회차가 있으면 끝날 때까지 기다린다(락 스킵을 비정상 종료로 세지 않게)
while pgrep -f "worker/pipeline.py" >/dev/null; do sleep 20; done
crashed=0
for i in $(seq 1 "${DRAIN_MAX_ROUNDS:-100}"); do
  before=$(grep -c '^{"videos"' "$LOG")
  MUKMAP_MAX_VIDEOS="${DRAIN_BATCH:-100}" MUKMAP_MAX_MINUTES=55 bash scripts/cron_mukmap.sh
  if [ "$(grep -c '^{"videos"' "$LOG")" -eq "$before" ]; then
    crashed=$((crashed + 1))
    echo "[drain $i] 결과 줄 없음(회차 비정상 종료 또는 락 스킵) $crashed/3"
    [ "$crashed" -ge 3 ] && { echo "[drain] 종료: 연속 비정상 종료"; break; }
    sleep 60
    continue
  fi
  crashed=0
  last=$(grep '^{"videos"' "$LOG" | tail -1)
  echo "[drain $i] $last"
  case "$last" in
    *'"videos": 0,'*|*'"blocked"'*) echo "[drain] 종료: 남은 자막 없음 또는 막힘"; break ;;
  esac
done

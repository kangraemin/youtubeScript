#!/bin/bash
# 6년치 먹방 자막을 몰아서 받는다: cron_food_backfill.sh를 채널당 FOOD_CAP개씩 반복하고,
# 받을 때마다 drain_mukmap.sh로 맛집을 뽑는다. 완료 마커가 생기거나, 연속 2회 새로 받은 게 0이면(차단 의심) 멈춘다.
cd /Users/ram/programming/vibecoding/youtubeScript
LOG="rawdata/transcripts/_food_backfill.log"
DONE="rawdata/transcripts/.food_backfill_done"
export FOOD_CAP="${FOOD_CAP:-30}" FOOD_MAX_MINUTES="${FOOD_MAX_MINUTES:-50}"
zero=0
for i in $(seq 1 200); do
  before=$(wc -l < "$LOG")
  bash scripts/cron_food_backfill.sh
  ok=$(tail -n +"$((before + 1))" "$LOG" | grep -o 'ok=[0-9]*' | cut -d= -f2 | paste -sd+ - | bc)
  echo "[food $i] $(date '+%F %T') 새 자막 ${ok:-0}개 / $(tail -n +"$((before + 1))" "$LOG" | grep '남은 영상 합계' | tail -1)"
  [ -f "$DONE" ] && { echo "[food] 백필 완료"; bash scripts/drain_mukmap.sh; break; }
  if [ "${ok:-0}" -eq 0 ]; then
    zero=$((zero + 1)); [ "$zero" -ge 2 ] && { echo "[food] 연속 2회 0개 — 차단 의심, 중단"; break; }
    sleep 600; continue
  fi
  zero=0
  bash scripts/drain_mukmap.sh
done

#!/bin/bash
# rawdata → DB upsert + duration_sec 채우기. 크롤과 독립 스케줄(매시 :40).
# 크롤 락(.crawl.lock)과는 별개의 락을 쓴다 — upload는 Playwright를 띄우지 않으므로
# 크롤과 동시에 돌아도 되고, 크롤이 몇 시간 걸려도 인질로 잡히지 않아야 한다.
SELF="/Users/ram/programming/vibecoding/youtubeScript/scripts/cron_upload.sh"
cd /Users/ram/programming/vibecoding/youtubeScript
mkdir -p rawdata/transcripts

LOG=rawdata/transcripts/_cron_upload.log
LOCK=rawdata/transcripts/.upload.lock
if [ -z "${UPLOAD_LOCK_HELD:-}" ]; then
  export UPLOAD_LOCK_HELD=1
  rc=0
  /usr/bin/lockf -k -s -t 0 "$LOCK" "$SELF" "$@" || rc=$?
  if [ "$rc" -eq 75 ]; then
    # EX_TEMPFAIL — 앞선 업로드가 아직 도는 중. 다음 회차에 처리한다.
    echo "[$(date '+%F %T')] 업로드 락 점유 중 — 이번 회차 스킵" >> "$LOG"
    exit 0
  fi
  exit "$rc"
fi

source .env.local
echo "[$(date '+%F %T')] upload 시작" >> "$LOG"
# 한 단계 실패가 다음 단계를 막지 않게 각각 rc만 남긴다.
.venv/bin/python scripts/upload_transcripts.py >> "$LOG" 2>&1 || echo "[$(date '+%F %T')] upload 실패 rc=$?" >> "$LOG"
# 신규 적재분의 duration_sec 채우기 (웹 쇼츠 필터용). NULL인 행만 조회하므로 증분만 처리된다.
.venv/bin/python scripts/backfill_duration.py >> "$LOG" 2>&1 || echo "[$(date '+%F %T')] duration 실패 rc=$?" >> "$LOG"
echo "[$(date '+%F %T')] upload 끝" >> "$LOG"

#!/bin/bash
# NULL transcript 자동 수집 + DB 업로드 (cron용)
SELF="/Users/ram/programming/vibecoding/youtubeScript/scripts/cron_backfill.sh"
cd /Users/ram/programming/vibecoding/youtubeScript
mkdir -p rawdata/transcripts

LOG="rawdata/transcripts/_cron_auto.log"

# run-crawl.sh와 **같은** 락을 공유한다. 둘 다 Playwright를 띄우므로 중첩되면
# 소켓이 고갈돼 전 채널이 [Errno 49] Can't assign requested address로 죽는다 (2026-08-15 사고).
# lockf는 flock(2) 커널 락이라 프로세스가 kill -9로 죽어도 자동 해제된다 (shlock은 stale이 남음).
LOCK=rawdata/transcripts/.crawl.lock
if [ -z "${BACKFILL_LOCK_HELD:-}" ]; then
  export BACKFILL_LOCK_HELD=1
  rc=0
  /usr/bin/lockf -k -s -t 0 "$LOCK" "$SELF" "$@" || rc=$?
  if [ "$rc" -eq 75 ]; then
    # EX_TEMPFAIL — 크롤이 아직 돌고 있다. 다음 회차에 처리한다.
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] 크롤 락 점유 중 — 이번 회차 스킵" >> "$LOG"
    exit 0
  fi
  exit "$rc"
fi

source .env.local 2>/dev/null || true

echo "[$(date '+%Y-%m-%d %H:%M:%S')] 시작" >> "$LOG"

# DB에서 NULL 영상 목록 가져와서 Playwright로 수집 + 바로 업로드
.venv/bin/python scripts/backfill_from_db.py --headless >> "$LOG" 2>&1

echo "[$(date '+%Y-%m-%d %H:%M:%S')] 완료" >> "$LOG"

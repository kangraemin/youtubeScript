#!/bin/bash
set -e
SELF="/Users/ram/programming/vibecoding/youtubeScript/run-crawl.sh"
cd /Users/ram/programming/vibecoding/youtubeScript
mkdir -p rawdata/transcripts

# run-crawl과 cron_backfill은 둘 다 Playwright를 띄운다. 중첩되면 소켓이 고갈돼
# 전 채널이 [Errno 49] Can't assign requested address로 죽는다 (2026-08-15 사고, 17일간 수집 0건).
# 둘이 같은 락을 공유해 상호 중첩까지 막는다.
# macOS엔 flock(1)이 없다. shlock은 죽은 PID를 인식하고도 "lock time changed"로 탈취를 거부해
# kill -9 시 락이 영구히 남는다(실측). lockf는 flock(2) 커널 락이라 프로세스가 어떻게 죽든
# OS가 자동 해제하므로 stale 상태가 없다. man shlock도 lockf 사용을 권고한다.
LOCK=rawdata/transcripts/.crawl.lock
if [ -z "${CRAWL_LOCK_HELD:-}" ]; then
  export CRAWL_LOCK_HELD=1
  rc=0
  /usr/bin/lockf -k -s -t 0 "$LOCK" "$SELF" "$@" || rc=$?
  if [ "$rc" -eq 75 ]; then
    # EX_TEMPFAIL — 락 획득 실패. 앞선 회차가 아직 돌고 있다는 뜻이므로 조용히 넘긴다.
    echo "[$(date '+%F %T')] 크롤 락 점유 중 — 이번 회차 스킵" >> rawdata/transcripts/_cron.log
    exit 0
  fi
  exit "$rc"
fi

source .env.local
.venv/bin/python scripts/crawl_youtube_transcripts.py --headless --workers 3 >> rawdata/transcripts/_cron.log 2>&1
.venv/bin/python scripts/upload_transcripts.py >> rawdata/transcripts/_cron.log 2>&1

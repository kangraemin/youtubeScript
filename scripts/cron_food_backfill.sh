#!/bin/bash
# 먹방 8채널 6년치(2190일) 자막 백필 — 매시 :50. 한 번에 다 받지 않고 회차마다 채널당 5개씩 나눠 받는다.
# 이미 받은 영상은 건너뛰므로 회차마다 이어서 받고, 남은 영상이 0이 되면 마커를 만들고 그 뒤로는 바로 끝난다.
SELF="/Users/ram/programming/vibecoding/youtubeScript/scripts/cron_food_backfill.sh"
cd /Users/ram/programming/vibecoding/youtubeScript
mkdir -p rawdata/transcripts

LOG="rawdata/transcripts/_food_backfill.log"
DONE="rawdata/transcripts/.food_backfill_done"
[ -f "$DONE" ] && exit 0

# run-crawl.sh·cron_backfill.sh와 같은 락을 공유한다(Playwright 중첩 시 소켓 고갈, 2026-08-15 사고)
LOCK=rawdata/transcripts/.crawl.lock
if [ -z "${FOOD_BACKFILL_LOCK_HELD:-}" ]; then
  export FOOD_BACKFILL_LOCK_HELD=1
  rc=0
  /usr/bin/lockf -k -s -t 0 "$LOCK" "$SELF" "$@" || rc=$?
  if [ "$rc" -eq 75 ]; then
    echo "[$(date '+%F %T')] 크롤 락 점유 중 — 이번 회차 스킵" >> "$LOG"
    exit 0
  fi
  exit "$rc"
fi

source .env.local 2>/dev/null || true
FOOD="dulcinea_studio,tzuyang,jaesunrang,kimjjamppong,kimsawon,heebab,sungsikyung,chureupkyeon"

echo "[$(date '+%F %T')] 시작" >> "$LOG"
OUT=$(.venv/bin/python scripts/crawl_youtube_transcripts.py --channel "$FOOD" --days 2190 \
  --crawl-cap 5 --headless --workers 1 --max-minutes 25 2>&1)
echo "$OUT" >> "$LOG"
if echo "$OUT" | grep -q "^BACKFILL COMPLETE"; then
  date '+%F %T' > "$DONE"
  echo "[$(date '+%F %T')] backfill complete — 다음 회차부터 건너뜀" >> "$LOG"
fi
echo "[$(date '+%F %T')] 완료" >> "$LOG"

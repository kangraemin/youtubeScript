#!/bin/bash
# NULL transcript 자동 수집 + DB 업로드 (cron용)
cd /Users/ram/programming/vibecoding/youtubeScript
source .env.local 2>/dev/null || true

LOG="rawdata/transcripts/_cron_auto.log"
echo "[$(date '+%Y-%m-%d %H:%M:%S')] 시작" >> "$LOG"

# DB에서 NULL 영상 목록 가져와서 Playwright로 수집 + 바로 업로드
python3 scripts/backfill_from_db.py --headless >> "$LOG" 2>&1

echo "[$(date '+%Y-%m-%d %H:%M:%S')] 완료" >> "$LOG"

#!/bin/bash
# MukMap 맛집 파이프라인 — 매시 :20. 자막 → claude -p 추출(막히면 codex exec) → 네이버 매칭 → Supabase.
# 쌓인 자막을 한 번에 비울 땐 MUKMAP_MAX_VIDEOS/MUKMAP_MAX_MINUTES로 회차 크기를 키운다(scripts/drain_mukmap.sh).
# 구독 한도를 아끼려고 회차당 10개만 처리한다(사용자 지시 2026-10-19). 6년치 백필은 2~3주에 걸쳐 따라간다.
# 하루 첫 회차에는 어제 리포트를 만든다.
SELF="/Users/ram/programming/vibecoding/youtubeScript/scripts/cron_mukmap.sh"
cd /Users/ram/programming/vibecoding/youtubeScript
mkdir -p rawdata/reports

LOG="rawdata/reports/_mukmap.log"
LOCK=rawdata/reports/.mukmap.lock
if [ -z "${MUKMAP_LOCK_HELD:-}" ]; then
  export MUKMAP_LOCK_HELD=1
  rc=0
  /usr/bin/lockf -k -s -t 0 "$LOCK" "$SELF" "$@" || rc=$?
  if [ "$rc" -eq 75 ]; then
    echo "[$(date '+%F %T')] 이전 회차가 아직 도는 중 — 스킵" >> "$LOG"
    exit 0
  fi
  exit "$rc"
fi

# cron은 PATH가 짧다 — claude CLI(~/.local/bin)와 homebrew를 넣는다
export PATH="$HOME/.local/bin:/opt/homebrew/bin:/usr/bin:/bin:$PATH"
# cron엔 계정 경로가 없어 기본 계정(~/.claude)으로 돈다 — 그 계정은 로그인 만료·주간 한도로 전부 실패했다(2026-10-19)
export CLAUDE_CONFIG_DIR="${CLAUDE_CONFIG_DIR:-/Users/ram/.config/claude-accounts/personal}"

echo "[$(date '+%F %T')] 시작" >> "$LOG"
.venv/bin/python worker/pipeline.py --max-videos "${MUKMAP_MAX_VIDEOS:-10}" --max-minutes "${MUKMAP_MAX_MINUTES:-50}" >> "$LOG" 2>&1

YESTERDAY=$(date -v-1d '+%F')
if [ ! -f "rawdata/reports/daily-$YESTERDAY.md" ]; then
  .venv/bin/python scripts/mukmap_daily_report.py --date "$YESTERDAY" >> "$LOG" 2>&1
fi
echo "[$(date '+%F %T')] 완료" >> "$LOG"

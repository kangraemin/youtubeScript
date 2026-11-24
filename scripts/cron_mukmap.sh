#!/bin/bash
# MukMap 맛집 파이프라인 — 매시 :20 (launchd com.ram.mukmap. cron은 키체인을 못 읽어 'Not logged in'으로 전부 실패해서 2026-10-22 옮김). 자막 → claude -p 추출 → 네이버 매칭 → Supabase.
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
# 기본 계정(~/.claude)은 CLAUDE_CONFIG_DIR를 비워야 로그인된다(경로를 직접 넣으면 "Not logged in", 2026-10-20). MUKMAP_CLAUDE=default로 고른다
[ "${MUKMAP_CLAUDE:-}" = default ] && unset CLAUDE_CONFIG_DIR
# 먹맵 키가 있으면 추출도 API 키로 돈다(구독 한도와 무관, 사용자 지시 10/31). MUKMAP_NO_API=1이면 구독으로
# 키 크레딧이 바닥나면(11/9~11/25 2주 동안 전부 실패) 구독으로 넘어간다(11/10 사용자 "claude -p 로 하게 하면되자나").
# 막힘 표시(~/.cache/mukmap-api-off)는 6시간 동안 믿고, 그 뒤 다시 시험해 키가 살아나면 키로 돌아간다. 번역(mukmap_translate.sh)도 같은 표시를 본다
API_OFF="$HOME/.cache/mukmap-api-off"
if [ -z "${MUKMAP_NO_API:-}" ]; then
  KEYLINE=$(grep '^MUKMAP_ANTHROPIC_API_KEY=' "$HOME/.claude/.env" 2>/dev/null)
  if [ -n "$KEYLINE" ] && [ -f "$API_OFF" ] && [ -n "$(find "$API_OFF" -mmin -360)" ]; then
    KEYLINE=""
  elif [ -n "$KEYLINE" ]; then
    if MUKMAP_ANTHROPIC_API_KEY="${KEYLINE#*=}" .venv/bin/python scripts/mukmap_key_ok.py >> "$LOG" 2>&1; then
      rm -f "$API_OFF"
    else
      echo "[$(date '+%F %T')] 먹맵 키 막힘 → 이번 6시간은 구독(claude -p)으로" >> "$LOG"
      mkdir -p "$(dirname "$API_OFF")"; touch "$API_OFF"; KEYLINE=""
    fi
  fi
  [ -n "$KEYLINE" ] && export MUKMAP_ANTHROPIC_API_KEY="${KEYLINE#*=}"
fi
# 로그인 토큰은 키체인에 있고 USER로 찾는다. cron엔 USER가 없어 "Not logged in"으로 전부 실패했다(2026-10-20)
export USER="${USER:-$(id -un)}"

echo "[$(date '+%F %T')] 시작" >> "$LOG"
.venv/bin/python worker/pipeline.py --max-videos "${MUKMAP_MAX_VIDEOS:-10}" --max-minutes "${MUKMAP_MAX_MINUTES:-50}" --workers "${MUKMAP_WORKERS:-1}" >> "$LOG" 2>&1
# 보류된 영상만 Chrome에서 열어 화면으로 다시 확인한다(회차당 5개, 내려받지 않음)
.venv/bin/python worker/frame_review.py --max 5 >> "$LOG" 2>&1
# 새 가게 영상을 외국어로 번역한다(회차당 30개)
bash scripts/mukmap_translate.sh >> "$LOG" 2>&1

YESTERDAY=$(date -v-1d '+%F')
if [ ! -f "rawdata/reports/daily-$YESTERDAY.md" ]; then
  .venv/bin/python scripts/mukmap_daily_report.py --date "$YESTERDAY" >> "$LOG" 2>&1
fi
echo "[$(date '+%F %T')] 완료" >> "$LOG"

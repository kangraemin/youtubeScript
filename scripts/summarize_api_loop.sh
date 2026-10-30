#!/bin/bash
# 경제 요약을 민구형 키(MUKMAP_ANTHROPIC_API_KEY)로 대기열이 빌 때까지 병렬로 돌린다(사용자 지시 10/31 "api key로 다해 한도없어").
# get_next_unsummarized.py가 행을 잡아(claim) 주므로 워커끼리 같은 영상을 겹쳐 잡지 않는다.
#   bash scripts/summarize_api_loop.sh [워커 수=4]
cd /Users/ram/programming/vibecoding/youtubeScript
KEYLINE=$(grep '^MUKMAP_ANTHROPIC_API_KEY=' "$HOME/.claude/.env")
export ANTHROPIC_API_KEY="${KEYLINE#*=}"
export PATH="$HOME/.local/bin:$PATH"
LOG=rawdata/reports/_summary_api.log
worker() {
  local miss=0
  while :; do
    out=$(claude -p "/summarize-next" --model "${SUMMARY_MODEL:-opus}" --dangerously-skip-permissions 2>&1 | tail -3)
    echo "[$(date '+%F %T')] w$1 $out" >> "$LOG"
    case "$out" in *"대기열 없음"*) break ;; esac
    case "$out" in *"Credit balance"*|*"limit"*|*"Invalid API key"*) echo "[w$1] 막힘" >> "$LOG"; break ;; esac
    if [ -z "$out" ]; then miss=$((miss+1)); [ $miss -ge 3 ] && break; else miss=0; fi
  done
}
for i in $(seq 1 "${1:-4}"); do worker "$i" & sleep 5; done
wait
echo "[$(date '+%F %T')] 끝" >> "$LOG"

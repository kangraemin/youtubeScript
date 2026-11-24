#!/bin/bash
# 새로 들어온 먹맵 가게 영상을 외국어(en/ja/zh-CN/zh-TW/vi)로 번역한다. cron_mukmap.sh가 매 회차 파이프라인 뒤에 부른다.
# 번역 스크립트는 웹 레포(mukmap/scripts/translate_i18n.py)에 있다. 먹맵 번역 키(MUKMAP_ANTHROPIC_API_KEY, ~/.claude/.env)가 있으면
# --api(Sonnet API, 회차당 MUKMAP_TRANSLATE_BUDGET 달러 상한)로, 없으면 claude -p(구독)로 번역한다. 이미 번역된 영상은 건너뛴다.
# 번역된 게 있으면 핀 묶음 파일을 언어마다 새로 써 두고 캐시를 비운다(mukmap/scripts/publish_pins.sh).
MUKMAP_DIR="${MUKMAP_DIR:-/Users/ram/programming/vibecoding/mukmap}"
MAX="${MUKMAP_TRANSLATE_MAX:-30}"
BUDGET="${MUKMAP_TRANSLATE_BUDGET:-1}"

# 손으로 돌리는 전체 번역이 살아 있으면 같은 영상을 두 번 번역하게 되므로 이번 회차는 넘긴다
if pgrep -f 'translate_i18n.py' >/dev/null; then
  echo "번역 스킵: 다른 번역이 도는 중"
  exit 0
fi

set -a
. "$MUKMAP_DIR/.env.local"
set +a
MODE=()
KEYLINE=$(grep '^MUKMAP_ANTHROPIC_API_KEY=' "$HOME/.claude/.env" 2>/dev/null)
# 키 크레딧이 바닥났다는 표시(cron_mukmap.sh가 6시간마다 다시 시험)가 있으면 구독(claude -p)으로 번역한다.
# 구독일 땐 주간 사용량 85%를 넘으면 새 묶음을 보내지 않는다
API_OFF="$HOME/.cache/mukmap-api-off"
SUBMODE=()
if [ -f "$API_OFF" ] && [ -n "$(find "$API_OFF" -mmin -360)" ]; then KEYLINE=""; SUBMODE=(--stop-usage 85); fi
# 하루 합계 상한(달러). 회차 상한만 있으면 매시간 돌아 하루 최대 24배가 된다(11/24 검토)
DAILY="${MUKMAP_TRANSLATE_DAILY:-3}"
SPENT_FILE="$HOME/.cache/mukmap-translate-$(date +%F)"
SPENT=$(cat "$SPENT_FILE" 2>/dev/null || echo 0)
LEFT=$(python3 -c "print(max(0.0, min($BUDGET, $DAILY - $SPENT)))")
rc=0; DONE=0
if [ -n "$KEYLINE" ] && python3 -c "import sys; sys.exit(0 if $LEFT < 0.05 else 1)"; then
  echo "번역 스킵: 오늘 쓴 돈 \$$SPENT (하루 상한 \$$DAILY)"
else
  if [ -n "$KEYLINE" ]; then
    export "$KEYLINE"
    MODE=(--api --budget "$LEFT")
  fi
  OUT=$(python3 "$MUKMAP_DIR/scripts/translate_i18n.py" "${MODE[@]}" "${SUBMODE[@]}" 1 "$MAX" 2>&1)
  rc=$?
  echo "$OUT"
  DONE=$(echo "$OUT" | awk '/^done /{n=$2} END{print n+0}')
  COST=$(echo "$OUT" | sed -nE 's/.*cost \$([0-9.]+).*/\1/p' | tail -1)
  [ -n "$COST" ] && python3 -c "print(round($SPENT + $COST, 4))" > "$SPENT_FILE"
fi
# 핀·사이트 데이터 파일을 다시 쓰고, 지난 파일과 비교해 바뀐 가게 페이지만 새로 그린다(publish_pins.sh).
# 번역이 있었거나, 수집이 가게를 바꿨거나(.mukmap.changed), 하루 한 번(04시: 폐업 숨김·합치기처럼 표시를 안 남기는 변경)
FLAG="$(dirname "$0")/../rawdata/reports/.mukmap.changed"
# 표시 파일은 게시 전에 옮겨 둔다. 게시 중에 수집이 새로 적은 표시를 같이 지우지 않게. 실패하면 되돌려 다음 회차가 다시 한다
if [ "$DONE" -gt 0 ] || [ -s "$FLAG" ] || [ "$(date +%H)" = 04 ]; then
  [ -f "$FLAG" ] && mv "$FLAG" "$FLAG.run"
  if bash "$MUKMAP_DIR/scripts/publish_pins.sh"; then rm -f "$FLAG.run"
  elif [ -f "$FLAG.run" ]; then cat "$FLAG.run" >> "$FLAG"; rm -f "$FLAG.run"; fi
fi
exit "$rc"

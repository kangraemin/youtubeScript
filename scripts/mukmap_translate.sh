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
if [ -n "$KEYLINE" ]; then
  export "$KEYLINE"
  MODE=(--api --budget "$BUDGET")
fi
OUT=$(python3 "$MUKMAP_DIR/scripts/translate_i18n.py" "${MODE[@]}" 1 "$MAX" 2>&1)
rc=$?
echo "$OUT"
DONE=$(echo "$OUT" | awk '/^done /{n=$2} END{print n+0}')
if [ "$DONE" -gt 0 ]; then
  bash "$MUKMAP_DIR/scripts/publish_pins.sh"
fi
exit "$rc"

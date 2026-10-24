#!/bin/bash
# 새로 들어온 먹맵 가게 영상을 외국어(en/ja/zh-CN/zh-TW)로 번역한다. cron_mukmap.sh가 매 회차 파이프라인 뒤에 부른다.
# 번역 스크립트는 웹 레포(mukmap/scripts/translate_i18n.py)에 있고 claude -p(구독)만 쓴다. 이미 번역된 영상은 건너뛴다.
# 번역된 게 있으면 사이트 캐시를 비워 바로 외국어 화면에 나오게 한다.
MUKMAP_DIR="${MUKMAP_DIR:-/Users/ram/programming/vibecoding/mukmap}"
MAX="${MUKMAP_TRANSLATE_MAX:-30}"

# 손으로 돌리는 전체 번역이 살아 있으면 같은 영상을 두 번 번역하게 되므로 이번 회차는 넘긴다
if pgrep -f 'translate_i18n.py' >/dev/null; then
  echo "번역 스킵: 다른 번역이 도는 중"
  exit 0
fi

set -a
. "$MUKMAP_DIR/.env.local"
set +a
OUT=$(python3 "$MUKMAP_DIR/scripts/translate_i18n.py" 1 "$MAX" 2>&1)
rc=$?
echo "$OUT"
DONE=$(echo "$OUT" | awk '/^done /{n=$2} END{print n+0}')
if [ "$DONE" -gt 0 ] && [ -n "${MUKMAP_BASE_URL:-}" ] && [ -n "${REVALIDATE_SECRET:-}" ]; then
  curl -s -o /dev/null -w "revalidate %{http_code}\n" -X POST -H "x-revalidate-secret: $REVALIDATE_SECRET" "${MUKMAP_BASE_URL%/}/api/revalidate"
fi
exit "$rc"

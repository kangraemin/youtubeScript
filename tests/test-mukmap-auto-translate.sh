#!/bin/bash
# tests/test-mukmap-auto-translate.sh
# 매시 먹맵 회차가 새 가게 영상을 외국어로 번역하고, 번역된 게 있으면 사이트 캐시를 비운다.
# 배경: 2026-10-25 외국어 번역을 손으로 한 번만 돌려서 그 뒤 들어온 가게는 번역되지 않았다.
set -e
cd "$(dirname "$0")/.."
PASS=0; FAIL=0
chk(){ if eval "$2"; then echo "✅ $1"; PASS=$((PASS+1)); else echo "❌ $1"; FAIL=$((FAIL+1)); fi; }

# 가짜 웹 레포(번역 스크립트·.env.local)와 가짜 curl/pgrep
fake(){
  T=$(mktemp -d)
  mkdir -p "$T/web/scripts" "$T/bin"
  printf 'MUKMAP_BASE_URL=http://stub.test\nREVALIDATE_SECRET=s3cret\n' > "$T/web/.env.local"
  cat > "$T/web/scripts/translate_i18n.py" <<EOF
import os, sys
open("$T/args", "w").write(" ".join(sys.argv[1:]) + " " + os.environ.get("REVALIDATE_SECRET", ""))
print("todo $1"); print("done $1 / $1")
EOF
  printf '#!/bin/bash\necho "$@" >> %s/curl\n' "$T" > "$T/bin/curl"
  printf '#!/bin/bash\nexit %s\n' "$2" > "$T/bin/pgrep"
  chmod +x "$T/bin/curl" "$T/bin/pgrep"
  echo "$T"
}
run(){ MUKMAP_DIR="$1/web" PATH="$1/bin:$PATH" bash scripts/mukmap_translate.sh > "$1/out" 2>&1; }

# TC-1: 다른 번역이 안 돌면 웹 레포 번역 스크립트를 동시 1개·회차 상한 30으로 부르고, .env.local 값을 넘긴다
T=$(fake 6 1); run "$T" || true
chk "TC-1 번역 실행(1 30, env 전달)" "[ \"\$(cat $T/args 2>/dev/null)\" = '1 30 s3cret' ]"

# TC-2: 번역된 게 있으면 /api/revalidate를 비밀값 헤더로 부른다
chk "TC-2 캐시 비우기" "grep -q 'x-revalidate-secret: s3cret' $T/curl 2>/dev/null && grep -q 'http://stub.test/api/revalidate' $T/curl"

# TC-3: 번역된 게 0이면 캐시를 비우지 않는다
T=$(fake 0 1); run "$T" || true
chk "TC-3 0건이면 캐시 그대로" "[ -f $T/args ] && [ ! -f $T/curl ]"

# TC-4: 손으로 돌리는 전체 번역이 살아 있으면 같은 영상을 두 번 번역하지 않게 건너뛴다
T=$(fake 6 0); run "$T" || true
chk "TC-4 다른 번역 중이면 스킵" "[ ! -f $T/args ] && grep -q '스킵' $T/out"

# TC-5: 회차 상한은 MUKMAP_TRANSLATE_MAX로 바꾼다
T=$(fake 6 1); MUKMAP_TRANSLATE_MAX=5 run "$T" || true
chk "TC-5 상한 조절" "[ \"\$(cut -d' ' -f1-2 $T/args 2>/dev/null)\" = '1 5' ]"

# TC-6: 매시 먹맵 회차(cron_mukmap.sh)가 파이프라인 뒤에 번역을 부른다
chk "TC-6 cron_mukmap 연결" "awk '/worker\/pipeline.py/{p=NR} /mukmap_translate.sh/{t=NR} END{exit !(p && t > p)}' scripts/cron_mukmap.sh"

echo "PASS=$PASS FAIL=$FAIL"
[ "$FAIL" -eq 0 ]

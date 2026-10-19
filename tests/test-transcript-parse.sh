#!/bin/bash
# tests/test-transcript-parse.sh
# 자막 파서: H:MM:SS를 시 단위로 읽고, 크롤러 헤더 4줄은 세그먼트에 넣지 않는다
set -e
cd "$(dirname "$0")/.."
PASS=0; FAIL=0
check(){ if eval "$2"; then echo "✅ $1"; PASS=$((PASS+1)); else echo "❌ $1"; FAIL=$((FAIL+1)); fi; }

TMP=$(mktemp -d)
mkdir -p "$TMP/ch"
printf '제목 1:23:45 들어간 제목\nhttps://www.youtube.com/watch?v=TESTVID\nvideo_id: TESTVID\ncollected_at: 2026-10-19T00:00:00\n\n0:05 y\n1:02:03 x\n이어지는 줄\n' > "$TMP/ch/TESTVID.txt"
PARSE=".venv/bin/python -c \"import sys; sys.path.insert(0,'worker'); from pathlib import Path; import transcript_fetcher as t; t._RAWDATA_DIR=Path('$TMP'); s=t.fetch_transcript('TESTVID')"

# TC-1: 0:05 → 5초
check "TC-1 M:SS" "$PARSE; assert s[0]['start']==5.0, s\""
# TC-2: 1:02:03 → 3723초 (예전엔 62초)
check "TC-2 H:MM:SS" "$PARSE; assert s[1]['start']==3723.0, s\""
# TC-3: 헤더 줄(제목·URL·video_id·collected_at)이 세그먼트에 없다
check "TC-3 헤더 제외" "$PARSE; assert len(s)==2 and not any('video_id' in x['text'] or 'http' in x['text'] for x in s), s\""
# TC-4: 타임스탬프 없는 줄은 앞 세그먼트에 이어 붙는다
check "TC-4 이어 붙이기" "$PARSE; assert s[1]['text']=='x 이어지는 줄', s\""

rm -rf "$TMP"
echo "PASS=$PASS FAIL=$FAIL"
[ "$FAIL" -eq 0 ]

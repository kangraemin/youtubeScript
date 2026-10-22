#!/bin/bash
# tests/test-whisper-all-missing.sh
# 자막 IP 차단 때 쓰는 whisper 전체 모드: shard가 겹치지 않고 빠짐없이 나누고, txt 있는 영상·whisper 실패·모아보기는 빼고 고른다
set -e
cd "$(dirname "$0")/.."
PASS=0; FAIL=0
check(){ if eval "$2"; then echo "✅ $1"; PASS=$((PASS+1)); else echo "❌ $1"; FAIL=$((FAIL+1)); fi; }
T=$(mktemp -d); trap 'rm -rf $T' EXIT
mkdir -p $T/higaengs && echo x > $T/higaengs/have00000aa.txt
echo '{"fail0000bbb": {"count": 1, "whisper_failed": true}}' > $T/higaengs/_failed.json

check "TC-1 shard 3등분이 겹치지 않고 전부 덮는다" ".venv/bin/python -c \"
from scripts.whisper_fallback import shard
xs=[{'vid':f'v{i:010d}'} for i in range(300)]
parts=[shard(xs,f'{i}/3') for i in range(3)]
ids=[c['vid'] for p in parts for c in p]
assert len(ids)==300 and len(set(ids))==300 and all(len(p)>50 for p in parts)\""

check "TC-2 txt 있음·whisper 실패·모아보기는 빼고 나머지를 고른다" ".venv/bin/python -c \"
import scripts.crawl_youtube_transcripts as c, googleapiclient.discovery as d
d.build=lambda *a,**k: None
v=lambda vid,t='맛집',s=600: {'vid':vid,'title':t,'url':'u','duration_sec':s}
c.get_channel_videos_api=lambda yt,ch,m,days: [v('have00000aa'),v('fail0000bbb'),v('comp0000ccc','몰아보기'),v('long0000ddd',s=9000),v('want0000eee')] if ch['slug']=='higaengs' else []
from scripts.whisper_fallback import all_missing
r=all_missing('$T',['higaengs'])
assert [x['vid'] for x in r]==['want0000eee'], r\""

echo "PASS=$PASS FAIL=$FAIL"
[ "$FAIL" -eq 0 ]

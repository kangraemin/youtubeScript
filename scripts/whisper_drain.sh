#!/bin/bash
# 유튜브가 자막 요청을 IP로 막을 때(IpBlocked·429) 남은 먹방 영상을 오디오 → 맥 Whisper로 받아 적는다.
# WHISPER_SHARDS개 프로세스가 영상을 나눠 받고(겹치지 않음), 그동안 10분마다 쌓인 자막을 맛집 추출(drain_mukmap.sh, 8개 동시)로 넘긴다.
# 사용: nohup bash scripts/whisper_drain.sh > rawdata/reports/_whisper_drain.out 2>&1 &
cd /Users/ram/programming/vibecoding/youtubeScript
N="${WHISPER_SHARDS:-2}"
pids=()
for i in $(seq 0 $((N - 1))); do
  .venv/bin/python scripts/whisper_fallback.py --all-missing --max-videos 0 --shard "$i/$N" --gap "${WHISPER_GAP:-10}" \
    > "rawdata/reports/_whisper_$i.log" 2>&1 &
  pids+=($!)
done
alive(){ for p in "${pids[@]}"; do kill -0 "$p" 2>/dev/null && return 0; done; return 1; }
while alive; do
  sleep 600
  bash scripts/drain_mukmap.sh
done
bash scripts/drain_mukmap.sh
echo "[whisper_drain] 끝 $(date '+%F %T')"

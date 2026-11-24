"""먹맵 API 키(MUKMAP_ANTHROPIC_API_KEY)가 지금 쓸 수 있는지 본다. 크레딧 부족·키 무효면 exit 1, 그 밖(망 오류 등)은 0.
11/9~11/25 크레딧이 바닥나 추출·번역이 2주 동안 전부 실패했다. 막히면 cron_mukmap.sh가 구독(claude -p)으로 넘어간다
(11/10 사용자 "claude -p 로 하게 하면되자나", 키 충전은 하지 않는다). 시험 호출은 Haiku 1토큰이라 비용이 거의 없다."""
import json, os, sys, urllib.error, urllib.request

key = os.environ.get("MUKMAP_ANTHROPIC_API_KEY")
if not key:
    sys.exit(1)
req = urllib.request.Request(
    "https://api.anthropic.com/v1/messages",
    data=json.dumps({"model": "claude-haiku-5-5", "max_tokens": 1,
                     "messages": [{"role": "user", "content": "1"}]}).encode(),
    headers={"x-api-key": key, "anthropic-version": "2023-06-01", "content-type": "application/json"})
try:
    urllib.request.urlopen(req, timeout=30).read()
except urllib.error.HTTPError as e:
    body = e.read().decode("utf-8", "replace")[:300]
    if e.code in (401, 403) or "credit balance" in body.lower():
        print(f"먹맵 키 막힘 {e.code}: {body[:120]}")
        sys.exit(1)
except Exception:
    pass
sys.exit(0)

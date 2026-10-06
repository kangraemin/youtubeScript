#!/usr/bin/env bash
# 크롤러: 스크립트 패널 실패 시 플레이어 timedtext(json3) 응답으로 대체
# 실행: bash tests/test-transcript-timedtext-fallback.sh
set -euo pipefail
cd "$(git rev-parse --show-toplevel)"
PY=python3
[ -x .venv/bin/python ] && PY=.venv/bin/python
$PY - <<'PY'
import sys
sys.path.insert(0, '.')
from scripts import crawl_youtube_transcripts as M
ok = True
def check(cond, msg):
    global ok
    print(("✅ " if cond else "❌ ") + msg); ok &= bool(cond)

def ev(ms, *words):
    return {"tStartMs": ms, "segs": [{"utf8": w} for w in words]}

# TC1: json3 파싱 — 빈 이벤트·개행 무시, 5초 단위로 묶기, 타임스탬프 형식
data = {"events": [
    {"tStartMs": 0},                       # segs 없음
    ev(1000, "안녕", "하세요"),
    {"tStartMs": 1500, "segs": [{"utf8": "\n"}]},  # 개행만
    ev(3000, "오늘은"),
    ev(7000, "금리"),
    ev(3_725_000, "끝"),
]}
segs = M.segments_from_json3(data)
check(segs == [
    {"timestamp": "0:01", "text": "안녕하세요 오늘은"},
    {"timestamp": "0:07", "text": "금리"},
    {"timestamp": "1:02:05", "text": "끝"},
], f"TC1 json3 → 세그먼트 {segs}")
check(M.segments_from_json3({}) == [] and M.segments_from_json3(None) == [], "TC2 빈 응답 → []")

# 가짜 page/response
class Resp:
    def __init__(s, url, data): s.url, s._d = url, data
    def json(s): return s._d
class Page:
    def __init__(s, fire): s.h, s.fire, s.removed = None, fire, False
    def on(s, ev, h): s.h = h
    def remove_listener(s, ev, h): s.removed = (h is s.h)
    def evaluate(s, js, arg=None):
        for r in s.fire: s.h(r)
        s.fire = []
        return "wait"

M.time.sleep = lambda *_: None
VID = "abcDEF12345"
good = {"events": [ev(2000, "본편", "자막")]}
ad = {"events": [ev(0, "광고")]}

# TC3: 패널 성공이면 패널 결과 그대로
M._get_transcript_panel = lambda p, v: [{"timestamp": "0:00", "text": "패널"}]
pg = Page([])
check(M.get_transcript(pg, VID) == [{"timestamp": "0:00", "text": "패널"}] and pg.removed, "TC3 패널 성공 시 패널 결과·리스너 해제")

# TC4: 패널 실패 → 광고(v 다름)·fmt 다름은 버리고 본편 json3만 사용
M._get_transcript_panel = lambda p, v: None
pg = Page([
    Resp(f"https://www.youtube.com/api/timedtext?v=AD000000000&fmt=json3", ad),
    Resp(f"https://www.youtube.com/api/timedtext?v={VID}&fmt=srv3", good),
    Resp(f"https://www.youtube.com/api/timedtext?v={VID}&fmt=json3&pot=x", good),
])
r = M.get_transcript(pg, VID)
check(r == [{"timestamp": "0:02", "text": "본편자막"}] and pg.removed, f"TC4 본편 timedtext 대체 {r}")

# TC5: 패널 실패 + 광고 자막만 → None
pg = Page([Resp("https://www.youtube.com/api/timedtext?v=AD000000000&fmt=json3", ad)])
check(M.get_transcript(pg, VID) is None and pg.removed, "TC5 광고 자막만 오면 None")

# TC6: 자막 이벤트가 비어 있는 본편 응답 → None
pg = Page([Resp(f"https://www.youtube.com/api/timedtext?v={VID}&fmt=json3", {"events": [{"tStartMs": 0}]})])
check(M.get_transcript(pg, VID) is None, "TC6 빈 본편 자막 → None")

sys.exit(0 if ok else 1)
PY
echo "ALL PASS"

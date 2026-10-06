#!/usr/bin/env bash
# E2E: 크롤러 소프트 스로틀 대응 — 패널 1회 대기 / 연속실패 서킷브레이커 / 런 상한 / heavy cap / upload 분리
# 실행: bash tests/test-crawl-circuit-breaker.sh
set -euo pipefail
cd "$(git rev-parse --show-toplevel)"
FAIL=0
PY=python3
[ -x .venv/bin/python ] && PY=.venv/bin/python

echo "### TC1: 구조"
if grep -n 'timeout=45000' scripts/crawl_youtube_transcripts.py; then
  echo "❌ 셀렉터별 45초 순차 대기 잔존"; FAIL=1
else
  echo "✅ 45초 순차 대기 없음"
fi
if grep -n 'upload_transcripts' run-crawl.sh | grep -v '^[0-9]*:#'; then
  echo "❌ run-crawl.sh가 아직 upload를 순차 실행"; FAIL=1
else
  echo "✅ run-crawl.sh에서 upload 분리"
fi
grep -q -- '--max-minutes' run-crawl.sh && echo "✅ run-crawl.sh 런 상한 지정" || { echo "❌ --max-minutes 없음"; FAIL=1; }
if [ -f scripts/cron_upload.sh ] && bash -n scripts/cron_upload.sh \
   && grep -qE '^LOCK=.*\.upload\.lock' scripts/cron_upload.sh \
   && ! grep -qE '^LOCK=.*\.crawl\.lock' scripts/cron_upload.sh; then
  echo "✅ cron_upload.sh 존재 · 문법 OK · 크롤과 별개 락"
else
  echo "❌ cron_upload.sh 누락/문법오류/락 공유"; FAIL=1
fi
bash -n run-crawl.sh && echo "✅ run-crawl.sh 문법 OK" || FAIL=1

echo "### TC2~TC7: 기능"
$PY - <<'PY' || FAIL=1
import json, sys, tempfile, time
from pathlib import Path
sys.path.insert(0, '.')
from scripts import crawl_youtube_transcripts as M
from playwright.sync_api import TimeoutError as PlaywrightTimeout

ok_all = True
def check(cond, msg):
    global ok_all
    print(("✅ " if cond else "❌ ") + msg)
    ok_all &= bool(cond)

# --- TC2: 패널 대기는 콤마 조인 1회, 15초 이하 ---
class _Btn:
    def is_visible(self): return True
    def click(self): pass
class _Kbd:
    def press(self, k): pass
class _Page:
    def __init__(self): self.waits = []; self.keyboard = _Kbd()
    def goto(self, *a, **k): pass
    def wait_for_timeout(self, *a, **k): pass
    def wait_for_load_state(self, *a, **k): pass
    def evaluate(self, *a, **k): return None
    def on(self, *a, **k): pass               # timedtext fallback 리스너
    def remove_listener(self, *a, **k): pass
    def query_selector(self, sel): return _Btn()
    def query_selector_all(self, sel): return [_Btn()]
    def wait_for_selector(self, sel, timeout=None, **k):
        self.waits.append((sel, timeout))
        if "transcript" in sel and ("segment" in sel):
            raise PlaywrightTimeout("simulated throttle")
        return _Btn()
M.time.sleep = lambda *_: None  # 클릭 후 대기 제거
pg = _Page()
res = M.get_transcript(pg, "VID")
seg_waits = [w for w in pg.waits if "segment" in w[0]]
check(res is None, "TC2 스로틀 시 None 반환")
check(len(seg_waits) == 1, f"TC2 세그먼트 대기 1회 (실제 {len(seg_waits)}회)")
check(seg_waits and "," in seg_waits[0][0], "TC2 셀렉터 콤마 조인")
check(seg_waits and seg_waits[0][1] <= 15000, f"TC2 타임아웃 ≤15s (실제 {seg_waits[0][1] if seg_waits else None})")

# --- process_channel stub 공통 ---
class _Ctx:
    def new_page(self): return object()
    def close(self): pass
class _Browser:
    def new_context(self, **k): return _Ctx()
    def close(self): pass
class _Chromium:
    def launch(self, **k): return _Browser()
class _PW:
    chromium = _Chromium()
    def __enter__(self): return self
    def __exit__(self, *a): return False
M.sync_playwright = lambda: _PW()
M.build = lambda *a, **k: None
M.save_transcript = lambda *a, **k: None
M.save_list_json = lambda *a, **k: None
tmp = tempfile.mkdtemp()

def run(slug, n, pattern, deadline=None):
    vids = [{"vid": f"V{i}", "title": "t", "url": "u", "meta": "2026-10-01"} for i in range(n)]
    M.get_channel_videos_api = lambda yt, ch, mx, d: vids
    calls = {"n": 0}
    def fake(page, vid):
        i = calls["n"]; calls["n"] += 1
        return [{"timestamp": "0:01", "text": "x"}] if pattern(i) else None
    M.get_transcript = fake
    r = M.process_channel({"slug": slug, "name": slug}, True, tmp, 0, 0, True, deadline)
    return calls["n"], r

# --- TC3: 전건 실패 → 8회 후 서킷 ---
n, r = run("alsangmoo", 50, lambda i: False)
check(n == M.CONSEC_FAIL_LIMIT == 8 and r["stopped"] == "circuit", f"TC3 연속실패 8건에서 조기 종료 (시도 {n}, stopped={r['stopped']})")

# --- TC4: 성공이 연속실패 카운터를 리셋 ---
n, r = run("alsangmoo", 50, lambda i: i == 7)  # 실패7 → 성공 → 실패8
check(n == 16 and r["ok"] == 1 and r["stopped"] == "circuit", f"TC4 성공 시 리셋 (시도 {n}, ok={r['ok']})")

# --- TC5: deadline 경과 → 시도 0 ---
n, r = run("alsangmoo", 50, lambda i: True, deadline=time.time() - 1)
check(n == 0 and r["stopped"] == "deadline", f"TC5 런 상한 경과 시 시도 0 (시도 {n}, stopped={r['stopped']})")

# --- TC6: heavy cap ---
n, r = run("sampro_tv", 100, lambda i: True)
check(n <= 30 and r["ok"] == n, f"TC6 heavy 채널 cap ≤30 (시도 {n})")
n, r = run("alsangmoo", 40, lambda i: True)
check(n == 40 and r["stopped"] is None, f"TC6' 일반 채널은 cap 없음 (시도 {n})")

# --- TC7: save_list_json 원자적 쓰기 ---
import importlib
M2 = importlib.reload(M)
d = tempfile.mkdtemp()
M2.save_list_json(d, "ch", [{"vid": "A", "title": "가"}])
p = Path(d) / "ch" / "_list.json"
check(p.exists() and json.loads(p.read_text())[0]["vid"] == "A", "TC7 _list.json 유효")
check(not list((Path(d) / "ch").glob("*.tmp")), "TC7 .tmp 잔존 없음")

sys.exit(0 if ok_all else 1)
PY

echo "### TC8: py_compile"
$PY -m py_compile scripts/crawl_youtube_transcripts.py scripts/channel_config.py && echo "✅ compile" || FAIL=1

echo "---"
[ $FAIL -eq 0 ] && echo "ALL PASS" || { echo "FAILED"; exit 1; }

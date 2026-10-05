#!/usr/bin/env bash
# backfill_from_db.py: 연속 실패 서킷브레이커 / 실행 시간 상한 / 중단 시 BATCH flush
# 실행: bash tests/test-backfill-circuit-breaker.sh
set -euo pipefail
cd "$(git rev-parse --show-toplevel)"
PY=python3
[ -x .venv/bin/python ] && PY=.venv/bin/python
$PY - <<'PY'
import sys, types, tempfile
from pathlib import Path
sys.path.insert(0, 'scripts'); sys.path.insert(0, 'worker')
import backfill_from_db as B

class Q:
    def __init__(s, db): s.db = db
    def select(s, *a): return s
    def eq(s, *a): return s
    def range(s, *a): return s
    def update(s, d): s.db.upd = d; return s
    def in_(s, k, v): s.db.updated.extend(v); return s
    def execute(s): return types.SimpleNamespace(data=s.db.rows if s.db.upd is None else [])
class DB:
    def __init__(s, rows): s.rows, s.updated, s.upd = rows, [], None
    def table(s, n): s.upd = None; return Q(s)
class PW:
    def __enter__(s):
        o = types.SimpleNamespace()
        ctx = types.SimpleNamespace(new_page=lambda: None, close=lambda: None)
        br = types.SimpleNamespace(new_context=lambda **k: ctx, close=lambda: None)
        o.chromium = types.SimpleNamespace(launch=lambda **k: br)
        return o
    def __exit__(s, *a): return False

tmp = Path(tempfile.mkdtemp())
B._ROOT = tmp
def save(d, slug, vid, *a):
    p = Path(d) / slug; p.mkdir(parents=True, exist_ok=True); (p / f"{vid}.txt").write_text("x")
B.save_transcript = save
B.sync_playwright = lambda: PW()
B.call_with_retry = lambda f: f()
ok = True
def run(n, good, argv):
    global calls
    rows = [{"vid": f"v{i}", "channel_slug": "c", "title": "", "url": ""} for i in range(n)]
    db = DB(rows); B.get_client = lambda: db
    calls = 0
    def gt(page, vid):
        global calls; calls += 1
        return [{"t": 1}] if vid in good else None
    B.get_transcript = gt
    sys.argv = ["x"] + argv
    B.main()
    return db, calls

# TC1: 3개 성공 후 연속 실패 → LIMIT회에서 중단, 성공분은 flush
db, c = run(100, {"v0", "v1", "v2"}, [])
cond = c == 3 + B.CONSEC_FAIL_LIMIT and db.updated == ["v0", "v1", "v2"]
print(("✅" if cond else "❌"), f"TC1 서킷브레이커 calls={c} flushed={db.updated}"); ok &= cond
# TC2: 중간 성공이 연속 카운터를 리셋
good = {f"v{i}" for i in range(0, 40, B.CONSEC_FAIL_LIMIT - 1)}
db, c = run(40, good, [])
cond = c == 40
print(("✅" if cond else "❌"), f"TC2 성공 시 카운터 리셋 calls={c}"); ok &= cond
# TC3: 상한 0분 → 하나도 안 돌고 종료
db, c = run(10, {"v0"}, ["--max-minutes", "0"])
cond = c == 0
print(("✅" if cond else "❌"), f"TC3 실행 시간 상한 calls={c}"); ok &= cond
sys.exit(0 if ok else 1)
PY

#!/bin/bash
# 화면 확인 판정이 이름과 지역이 모두 맞을 때만 통과하고, 지도에 보이는 가게에만 붙고, 실패한 영상은 다음에 다시 보는지 본다
cd "$(dirname "$0")/.." || exit 1
.venv/bin/python - <<'PY'
import json, sys, tempfile
from pathlib import Path
sys.path[:0] = ["worker"]
import frame_review as fr, supabase_client

A = "서울특별시 동대문구 한천로18길 14-2"
ok = dict(name_seen=True, other_store="", place="none", place_text="")
d = lambda j, hint="서울 동대문구 장안동", ex="장안곱창", found="장안곱창": fr.decide(j, hint, A, ex, found)
cases = [
    ("이름+자막 지역", d(ok), "approve"),
    ("이름+화면 지역", d({**ok, "place": "match", "place_text": "장안동"}, hint=""), "approve"),
    ("이름 없음", d({**ok, "name_seen": False}), "hold"),
    ("이름만 있고 지역 없음", d(ok, hint=""), "hold"),
    ("화면 지역이 다름", d({**ok, "place": "conflict"}), "hold"),
    ("다른 가게가 보임", d({**ok, "other_store": "연동회관"}), "hold"),
    ("자막 지역이 다름", d(ok, hint="서울 강남구 압구정"), "hold"),
    ("뽑은 이름이 다른 가게", d(ok, ex="더채운김밥", found="사이먼커피"), "hold"),
    ("name_seen이 글자", d({**ok, "name_seen": "true"}), "hold"),
    ("답을 못 읽음", d(None), "hold"),
    ("글자 없는 place match", d({**ok, "place": "match"}, hint=""), "hold"),
]
bad = [c for c in cases if c[1] != c[2]]
assert fr.parse_answer('설명 {"name_seen": true} 끝') == {"name_seen": True}
assert fr.parse_answer("JSON 아님") is None

tmp = Path(tempfile.mkdtemp())
fr.SKIP_DIR, fr.DONE_FILE = tmp, tmp / "out" / "reviewed.jsonl"
entry = dict(reason="low_confidence_visible_store", video_id="v1", channel_id="c1", title="t",
             extracted=dict(name="장안곱창", address_hint="서울 동대문구"),
             matched=dict(name="장안곱창", address=A, naver_place_id="1"),
             rest=dict(name="장안곱창", rating="추천"), video=dict(thumbnail_url="th", published_at="2026-01-01"))
(tmp / "2026-11-05.jsonl").write_text("\n".join([json.dumps(entry), json.dumps({**entry, "reason": "closed"}), "깨진 줄"]) + "\n")
assert [e["video_id"] for e in fr.held_entries()] == ["v1"]

saved = []
supabase_client.upsert_video = lambda db, row: saved.append(row)
supabase_client.find_restaurant = lambda db, r: dict(id=7, is_visible=True)
assert fr.attach(None, entry) is True and saved[0]["restaurant_id"] == 7 and saved[0]["thumbnail_url"] == "th"
saved.clear()
supabase_client.find_restaurant = lambda db, r: dict(id=7, is_visible=False)
assert fr.attach(None, entry) is False and not saved

supabase_client.get_client = lambda: None
fr.capture_sheet = lambda *a: (_ for _ in ()).throw(RuntimeError("크롬 안 열림"))
sys.argv = ["frame_review"]
fr.main()
assert fr.reviewed_keys() == set(), "한 번 실패한 영상이 끝난 것으로 기록됨"
fr.main(); fr.main()
assert fr.reviewed_keys() == {"v1|1"}, "세 번 실패한 영상이 앞줄을 계속 막음"
fr.DONE_FILE.unlink()
import subprocess
def _hang(*a):
    raise subprocess.TimeoutExpired("osascript", 20)
fr.capture_sheet = _hang
fr.main()
assert not fr.DONE_FILE.exists(), "Chrome이 응답하지 않은 것이 영상 실패로 기록됨"

fr.capture_sheet = lambda vid, out: "sheet.jpg"
fr.judge = lambda *a: dict(ok)
supabase_client.find_restaurant = lambda db, r: dict(id=7, is_visible=True)
fr.main()
fr.main()
rows = [json.loads(x) for x in fr.DONE_FILE.read_text().splitlines()]
assert len(rows) == 1 and rows[0]["attached"] is True and len(saved) == 1, rows

for name, got, want in cases:
    print("ok" if got == want else "FAIL", name, got)
sys.exit(1 if bad else 0)
PY

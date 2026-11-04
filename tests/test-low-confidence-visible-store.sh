#!/bin/bash
# 확신 낮은 영상은 이미 보이는 가게에 붙지 않고, 새 가게면 숨긴 채 저장되고, 확신 높으면 그대로 붙는지 본다
cd "$(dirname "$0")/.." || exit 1
.venv/bin/python - <<'PY'
import sys
sys.path[:0] = ["worker"]
import pipeline, supabase_client


class R:
    def __init__(self, data): self.data = data


class Q:
    def __init__(self, db, table): self.db, self.table, self.f, self.op, self.body = db, table, {}, "select", None
    def select(self, *a): return self
    def limit(self, *a): return self
    def eq(self, k, v): self.f[k] = v; return self
    def is_(self, k, v): self.f[k] = None; return self
    def insert(self, b): self.op, self.body = "insert", b; return self
    def update(self, b): self.op, self.body = "update", b; return self
    def upsert(self, b, **k): self.op, self.body = "upsert", b; return self
    def execute(self):
        rows = self.db.rows[self.table]
        if self.op == "select":
            return R([r for r in rows if all(r.get(k) == v for k, v in self.f.items())])
        if self.op == "insert":
            r = {**self.body, "id": len(rows) + 100}; rows.append(r); return R([r])
        if self.op == "upsert":
            rows.append(self.body); return R([self.body])
        return R([])


class DB:
    def __init__(self, stores): self.rows = {"restaurants": stores, "videos": []}
    def table(self, t): return Q(self, t)


pipeline._video_row = lambda v, rid, rest: {"video_id": v["video_id"], "restaurant_id": rid}
video = {"video_id": "v1"}
place = {"name": "우정", "address": "서울 종로구 인사동16길 3-1", "naver_place_id": "n1", "lat": 1, "lng": 2}

# 확신 낮음 + 보이는 가게 → 연결 안 함
db = DB([{"id": 1, "naver_place_id": "n1", "is_visible": True, "name": "우정"}])
out = []
assert pipeline._save(db, video, place, {}, False, out) is False
assert db.rows["videos"] == [] and out == []

# 확신 높음 + 보이는 가게 → 연결
db = DB([{"id": 1, "naver_place_id": "n1", "is_visible": True, "name": "우정"}])
out = []
assert pipeline._save(db, video, place, {}, True, out) is True
assert db.rows["videos"] == [{"video_id": "v1", "restaurant_id": 1}] and len(out) == 1

# 확신 낮음 + 숨긴 가게 → 숨긴 가게에 붙고, 보이게 바뀌지 않음
db = DB([{"id": 1, "naver_place_id": "n1", "is_visible": False, "name": "우정"}])
assert pipeline._save(db, video, place, {}, False, []) is True
assert db.rows["videos"][0]["restaurant_id"] == 1 and db.rows["restaurants"][0]["is_visible"] is False

# 확신 낮음 + 새 가게 → 숨긴 채 검수 대기로 저장
db = DB([])
assert pipeline._save(db, video, place, {}, False, []) is True
new = db.rows["restaurants"][0]
assert new["is_visible"] is False and new["needs_review"] is True and db.rows["videos"]

# 미리보기(db 없음)는 저장 없이 통과
out = []
assert pipeline._save(None, video, place, {}, False, out) is True and len(out) == 1

# 네이버 id가 없으면 이름·주소로 찾는다
db = DB([{"id": 7, "name": "우정", "address": place["address"], "is_visible": True}])
assert supabase_client.find_restaurant(db, {**place, "naver_place_id": None})["id"] == 7
print("OK")
PY

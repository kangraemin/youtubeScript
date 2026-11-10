"""시·도 표기만 달라 두 번 들어간 같은 가게를 하나로 합친다(먹맵 중복 185묶음, 2026-11-10).

  python3 scripts/merge_duplicate_restaurants.py            # 미리보기만(묶음 수·예시)
  python3 scripts/merge_duplicate_restaurants.py --map-only # DB는 그대로 두고 먹맵 주소 이동표만 쓴다(301 먼저 배포할 때)
  python3 scripts/merge_duplicate_restaurants.py --apply    # 실제로 합친다

- 같은 가게 판정은 worker/address_key.same_place(이름 같음 + 시·도 뗀 주소 같음 + 300m 안).
- 남기는 쪽은 id가 가장 작은 행(먼저 생겨 검색 기록이 있을 가능성이 큰 쪽).
- 버리는 쪽의 videos·alert_near 행은 남기는 쪽으로 옮긴다. 같은 영상이 이미 붙어 있으면 버리는 쪽 행을 지운다.
- 남기는 쪽에 naver_place_id가 없으면 버리는 쪽 것을 가져온다.
- 버리는 쪽은 is_visible=false로 숨기고(지우지 않는다) 장소 ID를 비우고 이름 앞에 '[merged→남긴 id]'를 단다(수집기가 다시 못 잡게).
- 옛 주소(/restaurant/<버린 id>)를 남긴 쪽으로 301 하도록 먹맵 lib/merged-restaurants.json에 {버린 id: 남긴 id}를 더한다.
"""
import argparse
import collections
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "worker"))
from address_key import same_place  # noqa: E402
from supabase_client import get_client  # noqa: E402

MAP_FILE = ROOT.parent / "mukmap" / "lib" / "merged-restaurants.json"


def load_all(db):
    rows, off = [], 0
    while True:
        b = (db.table("restaurants").select("id,name,address,lat,lng,naver_place_id,is_visible,closed_at")
             .eq("is_visible", True).is_("closed_at", "null").order("id").range(off, off + 999).execute()).data
        rows += b
        off += 1000
        if len(b) < 1000:
            return rows


def groups_of(rows):
    by_name = collections.defaultdict(list)
    for r in rows:
        by_name[(r["name"] or "").replace(" ", "")].append(r)
    out = []
    for same in by_name.values():
        if len(same) < 2:
            continue
        used = set()
        for i, a in enumerate(same):
            if a["id"] in used:
                continue
            g = [a] + [b for b in same[i + 1:] if b["id"] not in used and same_place(a, b)]
            if len(g) > 1:
                used.update(x["id"] for x in g)
                out.append(sorted(g, key=lambda x: x["id"]))
    return out


def merge(db, keep, drop):
    kv = {v["video_id"] for v in db.table("videos").select("video_id").eq("restaurant_id", keep["id"]).execute().data}
    moved = deleted = 0
    for v in db.table("videos").select("id,video_id").eq("restaurant_id", drop["id"]).execute().data:
        if v["video_id"] in kv:
            db.table("videos").delete().eq("id", v["id"]).execute()
            deleted += 1
        else:
            db.table("videos").update({"restaurant_id": keep["id"]}).eq("id", v["id"]).execute()
            kv.add(v["video_id"])
            moved += 1
    ka = {a["anon_key"] for a in db.table("alert_near").select("anon_key").eq("restaurant_id", keep["id"]).execute().data}
    for a in db.table("alert_near").select("*").eq("restaurant_id", drop["id"]).execute().data:
        db.table("alert_near").delete().eq("anon_key", a["anon_key"]).eq("restaurant_id", drop["id"]).execute()
        if a["anon_key"] not in ka:
            db.table("alert_near").insert({**a, "restaurant_id": keep["id"]}).execute()
    # 숨긴 행이 수집기(find_restaurant: 장소 ID → 이름+주소)에 다시 잡혀 영상이 안 보이는 쪽에 붙지 않게
    # 장소 ID를 비우고 이름 앞에 표시를 단다
    db.table("restaurants").update({"is_visible": False, "naver_place_id": None,
                                    "name": f"[merged→{keep['id']}] {drop['name']}"}).eq("id", drop["id"]).execute()
    if not keep.get("naver_place_id") and drop.get("naver_place_id"):
        db.table("restaurants").update({"naver_place_id": drop["naver_place_id"]}).eq("id", keep["id"]).execute()
        keep["naver_place_id"] = drop["naver_place_id"]
    return moved, deleted


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--map-only", action="store_true")
    a = ap.parse_args()
    db = get_client()
    groups = groups_of(load_all(db))
    print(f"묶음 {len(groups)}개, 숨길 행 {sum(len(g) - 1 for g in groups)}개")
    for g in groups[:5]:
        print(" ", [(x["id"], x["address"]) for x in g])
    mapping = json.loads(MAP_FILE.read_text()) if MAP_FILE.exists() else {}
    if a.map_only:
        for g in groups:
            for drop in g[1:]:
                mapping[str(drop["id"])] = g[0]["id"]
        MAP_FILE.write_text(json.dumps(dict(sorted(mapping.items(), key=lambda kv: int(kv[0]))), indent=1) + "\n")
        print(f"RESULT: 주소 이동표 {len(mapping)}개 → {MAP_FILE}")
        return
    if not a.apply:
        return
    tm = td = 0
    for g in groups:
        keep = g[0]
        for drop in g[1:]:
            m, d = merge(db, keep, drop)
            tm += m
            td += d
            mapping[str(drop["id"])] = keep["id"]
            MAP_FILE.write_text(json.dumps(dict(sorted(mapping.items(), key=lambda kv: int(kv[0]))), indent=1) + "\n")
    print(f"RESULT: 합침 {len(groups)}묶음, 영상 옮김 {tm}, 겹친 영상 지움 {td}, 주소 이동표 {len(mapping)}개 → {MAP_FILE}")


if __name__ == "__main__":
    main()

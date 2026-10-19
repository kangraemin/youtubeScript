"""검수 대기(needs_review) 가게를 고친 지역 매칭으로 다시 찾아본다.

영상에서 뽑은 이름·지역 힌트(processing_queue.extraction_result)로 네이버 지역검색을 다시 돌려
확신 high가 나오면 그 장소로 바로잡고 노출한다. 나머지는 그대로 검수 대기로 둔다.

    .venv/bin/python worker/reresolve_review.py            # 미리보기(DB 안 씀)
    .venv/bin/python worker/reresolve_review.py --apply
"""
import argparse
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from chain_blacklist import is_chain  # noqa: E402
from naver_search import _hint_regions, _region_score, name_close, name_similar, search_restaurant  # noqa: E402
from pipeline import load_env, region_city, trigger_revalidate  # noqa: E402
from supabase_client import get_client  # noqa: E402

REPORT = Path(__file__).resolve().parent.parent / "rawdata" / "reports" / "reresolve-review.json"


def _bigram_sim(a: str, b: str) -> float:
    a, b = a.replace(" ", ""), b.replace(" ", "")
    if not a or not b:
        return 0.0
    if a in b or b in a:
        return 1.0
    A = {a[i:i + 2] for i in range(len(a) - 1)}
    B = {b[i:i + 2] for i in range(len(b) - 1)}
    return len(A & B) / max(1, min(len(A), len(B)))


def _said_entry(extracted: list[dict], current_name: str) -> dict | None:
    """그 영상의 추출 결과 중 지금 가게 이름과 가장 닮은 항목(= 이 가게로 저장된 원래 이름)."""
    best, score = None, -1.0
    for e in extracted or []:
        s = _bigram_sim(e.get("name", ""), current_name)
        if s > score:
            best, score = e, s
    return best


def _linked_elsewhere(db, r: dict, said_name: str) -> bool:
    """같은 영상에 이어진 다른 가게 중 said_name과 같은 가게가 있는가."""
    for v in r["videos"]:
        rows = db.table("videos").select("restaurants(id,name)").eq("video_id", v["video_id"]).neq(
            "restaurant_id", r["id"]).execute().data or []
        if any(name_close(said_name, (x.get("restaurants") or {}).get("name", "")) for x in rows):
            return True
    return False


def _fetch_all(db, table: str, select: str, **eq) -> list[dict]:
    rows, off = [], 0
    while True:
        q = db.table(table).select(select)
        for k, v in eq.items():
            q = q.eq(k, v)
        page = q.range(off, off + 999).execute().data or []
        rows += page
        if len(page) < 1000:
            return rows
        off += 1000


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true")
    args = ap.parse_args()
    load_env()
    db = get_client()

    rests = _fetch_all(db, "restaurants", "id,name,address,videos(video_id)", needs_review=True)
    vids = sorted({v["video_id"] for r in rests for v in r["videos"]})
    extracted = {}
    for i in range(0, len(vids), 100):
        for q in db.table("processing_queue").select("video_id,extraction_result").in_(
                "video_id", vids[i:i + 100]).execute().data or []:
            er = q.get("extraction_result")
            extracted[q["video_id"]] = er if isinstance(er, list) else (er or {}).get("restaurants", [])

    out = {"approve_same": [], "moved": [], "merged": [], "kept": []}
    for r in rests:
        said = None
        for v in r["videos"]:
            said = _said_entry(extracted.get(v["video_id"]), r["name"])
            if said:
                break
        if not said:
            out["kept"].append({"id": r["id"], "name": r["name"], "why": "추출 기록 없음"})
            continue
        hint = said.get("address_hint", "") or ""
        far = _bigram_sim(said.get("name", ""), r["name"]) < 0.5
        if far and _linked_elsewhere(db, r, said["name"]):
            # 그 이름은 이미 이 영상의 다른 가게로 이어져 있다 → 이 행이 어디서 왔는지 몰라 손대지 않는다
            out["kept"].append({"id": r["id"], "name": r["name"], "said": said.get("name"), "hint": hint,
                                "why": "추출 이름과 다름"})
            continue
        time.sleep(0.25)  # 지역검색 API 초당 한도(429)
        loc = search_restaurant(said["name"], hint)
        if not loc or loc.get("lat") is None or loc.get("confidence") != "high" or is_chain(loc["name"]):
            out["kept"].append({"id": r["id"], "name": r["name"], "said": said["name"],
                                "hint": said.get("address_hint"), "found": loc and loc.get("address"),
                                "why": "확신 낮음" if loc else "검색 결과 없음"})
            continue
        item = {"id": r["id"], "old": [r["name"], r["address"]], "said": said["name"],
                "hint": said.get("address_hint"), "new": [loc["name"], loc["address"]]}
        if loc["address"] == r["address"] and name_similar(loc["name"], r["name"]):
            out["approve_same"].append(item)
            if args.apply:
                db.table("restaurants").update({"needs_review": False, "is_visible": True}).eq("id", r["id"]).execute()
            continue
        if r["address"] and _region_score(r["address"], _hint_regions(hint), hint) > 0:
            # 원래 주소도 힌트 지역과 맞다 → 둘 중 어느 쪽이 맞는지 모르니 사람이 본다
            out["kept"].append({**item, "why": "원래 주소도 지역 일치"})
            continue
        dup = db.table("restaurants").select("id").eq("name", loc["name"]).eq(
            "address", loc["address"]).neq("id", r["id"]).limit(1).execute().data
        if dup and far:
            out["kept"].append({**item, "why": "추출 이름과 다름(기존 가게 있음)"})
            continue
        if dup:
            # 이미 있는 가게 → 영상을 그쪽으로 옮기고 잘못 잡힌 행은 지운다
            item["into"] = dup[0]["id"]
            out["merged"].append(item)
            if args.apply:
                for v in r["videos"]:
                    taken = db.table("videos").select("id").eq("video_id", v["video_id"]).eq(
                        "restaurant_id", dup[0]["id"]).limit(1).execute().data
                    q = db.table("videos")
                    if taken:
                        q.delete().eq("video_id", v["video_id"]).eq("restaurant_id", r["id"]).execute()
                    else:
                        q.update({"restaurant_id": dup[0]["id"]}).eq("video_id", v["video_id"]).eq(
                            "restaurant_id", r["id"]).execute()
                db.table("restaurants").update({"is_visible": True}).eq("id", dup[0]["id"]).execute()
                db.table("restaurants").delete().eq("id", r["id"]).execute()
            continue
        out["moved"].append(item)
        if args.apply:
            region, city = region_city(loc["address"])
            db.table("restaurants").update({
                "name": loc["name"], "address": loc["address"], "lat": loc["lat"], "lng": loc["lng"],
                "region": loc.get("region") or region, "city": city,
                "needs_review": False, "is_visible": True,
            }).eq("id", r["id"]).execute()

    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps({k: len(v) for k, v in out.items()}, ensure_ascii=False), "apply" if args.apply else "dry-run")
    if args.apply:
        trigger_revalidate()


if __name__ == "__main__":
    main()

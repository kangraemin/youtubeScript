#!/usr/bin/env python3
"""폐업 가게 판정 + 월 1회 재점검.

확인한 사실 (2026-10-19 실측)
- m.place.naver.com/restaurant/<place_id>/home HTML의 window.__APOLLO_STATE__에
  PlaceDetailBase:<id>(이름·카테고리·주소·좌표)와 businessStatusDescription.status("영업 전" 등)가 들어 있다.
- 예전에 쓰던 map.naver.com/v5/api/place/summary/<id>는 301만 돌려준다(고장).
- 없는 place_id도 200을 돌려준다. 그래서 PlaceDetailBase가 없으면 "없는 가게"로 본다.
- 공식 지역검색 API는 place_id와 영업 상태를 주지 않는다.

Usage:
    python worker/closure_check.py --place 1556905994
    python worker/closure_check.py --recheck-all [--limit 500]
"""
import argparse
import json
import logging
import os
import re
import sys
import time
from datetime import datetime, timezone
from typing import Literal

import requests

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

logger = logging.getLogger(__name__)

PLACE_URL = "https://m.place.naver.com/restaurant/{place_id}/home"
UA = {"User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 Mobile/15E148"}
_STATE = re.compile(r"window\.__APOLLO_STATE__\s*=\s*")
_CLOSED = re.compile(r"폐업|영업\s*종료|휴업")


def fetch_place(place_id: str) -> dict | None:
    """place_id → {naver_place_id, name, category, address, lat, lng, status}. 페이지를 못 읽으면 None.

    status: "open" / "closed" / "unknown". 가게 정보가 아예 없으면 status="closed"로 돌려준다(없는 가게).
    """
    try:
        r = requests.get(PLACE_URL.format(place_id=place_id), headers=UA, timeout=10)
    except requests.RequestException as e:
        logger.warning("place page failed %s: %s", place_id, e)
        return None
    if r.status_code == 404:
        return {"naver_place_id": str(place_id), "status": "closed"}
    if r.status_code != 200:
        return None
    r.encoding = "utf-8"
    m = _STATE.search(r.text)
    if not m:
        return None
    try:
        state, _ = json.JSONDecoder().raw_decode(r.text, m.end())
    except json.JSONDecodeError:
        return None

    base = state.get(f"PlaceDetailBase:{place_id}")
    if not base:
        return {"naver_place_id": str(place_id), "status": "closed"}

    status = "open"
    for v in state.values():
        if isinstance(v, dict) and v.get("__typename") == "BusinessStatusDescription":
            text = f"{v.get('status') or ''} {v.get('description') or ''}"
            if _CLOSED.search(text):
                status = "closed"
            break
    if _CLOSED.search(base.get("name") or ""):
        status = "closed"

    coord = base.get("coordinate") or {}
    try:
        lat, lng = float(coord.get("y")), float(coord.get("x"))
    except (TypeError, ValueError):
        lat = lng = None
    return {
        "naver_place_id": str(place_id),
        "name": base.get("name"),
        "category": base.get("category"),
        "address": base.get("roadAddress") or base.get("address"),
        "lat": lat,
        "lng": lng,
        "status": status,
    }


def get_place_status(place_id: str) -> Literal["open", "closed", "unknown"]:
    info = fetch_place(place_id)
    return info["status"] if info else "unknown"


def _squash(s: str) -> str:
    return re.sub(r"\s+", "", s or "")


def _status_by_search(name: str, address: str, search) -> str:
    """place_id 없는 가게: 지역검색 결과에 같은 주소가 있으면 open.

    "주소 앞 두 단어 + 이름"과 "이름"으로 두 번 찾아도 없을 때만 closed. 검색이 둘 다 비면(API 오류일 수도) unknown.
    """
    prefix = " ".join(address.split()[:2])
    seen_any = False
    for query in (f"{prefix} {name}".strip(), name):
        items = search(query)
        seen_any = seen_any or bool(items)
        if any(_squash(it.get("roadAddress") or it.get("address")) == _squash(address) for it in items):
            return "open"
    return "closed" if seen_any else "unknown"


def recheck_all(limit: int = 0) -> dict:
    """저장된 보이는 가게를 다시 확인해 폐업이면 is_visible=false로 내린다.

    place_id가 있으면 플레이스 페이지로, 없으면 공식 지역검색에서 같은 도로명 주소가 나오는지로 본다.
    """
    from supabase_client import get_client
    from naver_search import _search_candidates

    db = get_client()
    q = (db.table("restaurants").select("id,name,address,naver_place_id")
         .eq("is_visible", True).order("closed_checked_at", desc=False, nullsfirst=True))
    rows = (q.limit(limit) if limit else q).execute().data or []
    now = datetime.now(timezone.utc).isoformat()
    stats = {"checked": 0, "closed": 0, "unknown": 0}
    for row in rows:
        if row.get("naver_place_id"):
            status = get_place_status(row["naver_place_id"])
        else:
            status = _status_by_search(row["name"], row.get("address") or "", _search_candidates)
        stats["checked"] += 1
        upd = {"closed_checked_at": now}
        if status == "closed":
            upd["is_visible"] = False
            stats["closed"] += 1
            logger.info("폐업 처리: %s (%s)", row["name"], row["address"])
        elif status == "unknown":
            stats["unknown"] += 1
        db.table("restaurants").update(upd).eq("id", row["id"]).execute()
        time.sleep(0.3)
    return stats


def main():
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
    p = argparse.ArgumentParser(description="네이버 플레이스 폐업 판정")
    p.add_argument("--place", help="place_id 하나 확인")
    p.add_argument("--recheck-all", action="store_true", help="저장된 가게 전체 재점검(월 1회)")
    p.add_argument("--limit", type=int, default=0)
    args = p.parse_args()
    if args.place:
        print(json.dumps(fetch_place(args.place), ensure_ascii=False))
    elif args.recheck_all:
        print(json.dumps(recheck_all(args.limit), ensure_ascii=False))
    else:
        p.print_help()


if __name__ == "__main__":
    main()

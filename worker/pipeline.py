#!/usr/bin/env python3
"""MukMap 맛집 파이프라인 — 받아 둔 먹방 자막 → 방문 식당 추출 → 네이버 매칭 → Supabase.

collect.py / main.py를 대체한다. 크론(scripts/cron_mukmap.sh)이 매시 조금씩 돌린다.

후보: rawdata/transcripts/<먹방 slug>/*.txt 전부(_list.json은 크롤 창(60일)마다 덮어써져서 쓰지 않는다)
      − processing_queue에서 이번 PROMPT_VERSION으로 끝난 것(done / no_restaurant) − 3회 넘게 실패한 것
처리 순서: 최신 영상부터.

Usage:
    python worker/pipeline.py --max-videos 10 --max-minutes 50
    python worker/pipeline.py --video-id QWY3eNslYn0 --dry-run
"""
import argparse
import json
import logging
import os
import re
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path

import httpx
from dotenv import load_dotenv
from googleapiclient.discovery import build

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from chain_blacklist import is_chain  # noqa: E402
from closure_check import get_place_status  # noqa: E402
from description_parser import parse_description_places  # noqa: E402
from naver_search import REGION_MAP, name_similar, search_restaurant  # noqa: E402
from restaurant_extractor import PROMPT_VERSION, ExtractBlocked, ExtractError, extract_restaurants  # noqa: E402
from skip_logger import log_skipped  # noqa: E402
from transcript_fetcher import fetch_transcript  # noqa: E402
from scripts.channel_config import food_channels, is_compilation  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("pipeline")

ROOT = Path(__file__).resolve().parent.parent
TRANSCRIPTS = ROOT / "rawdata" / "transcripts"
USAGE_LOG = ROOT / "rawdata" / "reports" / "pipeline-usage.jsonl"
# 추출 결과를 DB에 넣기 전에 먼저 여기에 둔다. DB가 죽어도 다시 추출하지 않고 이걸 쓴다(2026-10-20 DB 5시간 장애)
EXTRACT_DIR = ROOT / "rawdata" / "extract"


def _cached_extract(vid: str) -> list[dict] | None:
    f = EXTRACT_DIR / f"{vid}.json"
    if not f.exists():
        return None
    try:
        d = json.loads(f.read_text(encoding="utf-8"))
    except ValueError:
        return None
    return d["restaurants"] if d.get("prompt_version") == PROMPT_VERSION else None


def _keep_extract(vid: str, restaurants: list[dict]) -> None:
    EXTRACT_DIR.mkdir(parents=True, exist_ok=True)
    (EXTRACT_DIR / f"{vid}.json").write_text(
        json.dumps({"prompt_version": PROMPT_VERSION, "restaurants": restaurants}, ensure_ascii=False), encoding="utf-8")
MAX_RETRY = 3
FINISHED = ("done", "no_restaurant")


def load_env():
    load_dotenv(ROOT / ".env")
    load_dotenv(ROOT / ".env.local", override=False)
    os.environ.setdefault("SUPABASE_URL", os.environ.get("NEXT_PUBLIC_SUPABASE_URL", ""))
    os.environ.setdefault("SUPABASE_SERVICE_KEY", os.environ.get("SUPABASE_SERVICE_ROLE_KEY", ""))


def region_city(address: str | None) -> tuple[str | None, str | None]:
    """"광주 동구 ..." → ("광주", "동구"), "경기 수원시 팔달구 ..." → ("경기", "수원시")."""
    if not address:
        return None, None
    region = next((v for k, v in REGION_MAP.items() if k in address), None)
    words = address.split()
    city = words[1] if len(words) > 1 and re.search(r"[시군구]$", words[1]) else None
    return region, city


# ── 후보 ──────────────────────────────────────────────────────────────

def _published_dates() -> dict[str, str]:
    """vid → 게시일. 모아보기·2시간 초과 영상은 빈 값 대신 None으로 표시해 candidates가 건너뛴다."""
    out = {}
    for ch in food_channels():
        try:
            for v in json.loads((TRANSCRIPTS / ch["slug"] / "_list.json").read_text(encoding="utf-8")):
                if is_compilation(v.get("title", ""), v.get("duration_sec", 0)):
                    out[v["vid"]] = None
                    continue
                out[v["vid"]] = v.get("meta", "")
        except (FileNotFoundError, json.JSONDecodeError):
            continue
    return out


def _queue_state(db) -> dict[str, dict]:
    rows, start = [], 0
    while True:
        page = (db.table("processing_queue").select("video_id,status,retry_count,prompt_version")
                .range(start, start + 999).execute().data or [])
        rows += page
        if len(page) < 1000:
            break
        start += 1000
    return {r["video_id"]: r for r in rows}


VIDEO_ID = re.compile(r"^[A-Za-z0-9_-]{11}$")


def candidates(db, max_videos: int) -> list[dict]:
    dates = _published_dates()
    state = _queue_state(db) if db else {}
    out = []
    for ch in food_channels():
        for f in (TRANSCRIPTS / ch["slug"]).glob("*.txt"):
            vid = f.stem
            if not VIDEO_ID.match(vid):  # _no_transcript.txt 같은 표시용 파일
                continue
            if vid in dates and dates[vid] is None:  # 모아보기·2시간 초과 (원본 영상에 가게가 다 있다)
                continue
            q = state.get(vid)
            if q and q.get("prompt_version") == PROMPT_VERSION:
                if q["status"] in FINISHED or (q.get("retry_count") or 0) >= MAX_RETRY:
                    continue
            out.append({"video_id": vid, "channel_id": ch["id"], "slug": ch["slug"],
                        "published": dates.get(vid, "")})
    out.sort(key=lambda v: v["published"], reverse=True)
    return out[:max_videos] if max_videos else out


def enrich_metadata(youtube, videos: list[dict]) -> None:
    """videos.list(50개당 1 unit)로 제목·설명·썸네일·게시일을 채운다. metadata.json(5/5 이후 미갱신) 대체."""
    by_id = {v["video_id"]: v for v in videos}
    ids = list(by_id)
    for i in range(0, len(ids), 50):
        resp = youtube.videos().list(part="snippet", id=",".join(ids[i:i + 50])).execute()
        for it in resp.get("items", []):
            sn = it["snippet"]
            th = sn.get("thumbnails", {})
            by_id[it["id"]].update({
                "title": sn.get("title", ""),
                "description": sn.get("description", ""),
                "thumbnail_url": (th.get("medium") or th.get("high") or th.get("default") or {}).get("url"),
                "published_at": sn.get("publishedAt"),
            })
    for v in videos:
        v.setdefault("title", "")
        v.setdefault("description", "")
        v.setdefault("thumbnail_url", None)
        v.setdefault("published_at", None)


# ── 큐 ────────────────────────────────────────────────────────────────

def queue_set(db, video: dict, status: str, error: str | None = None, result: list | None = None):
    if db is None:
        return
    row = {"video_id": video["video_id"], "channel_id": video["channel_id"], "status": status,
           "prompt_version": PROMPT_VERSION, "error_message": error}
    if status == "failed":
        prev = db.table("processing_queue").select("retry_count,prompt_version").eq(
            "video_id", video["video_id"]).limit(1).execute().data
        same = prev and prev[0].get("prompt_version") == PROMPT_VERSION
        row["retry_count"] = ((prev[0].get("retry_count") or 0) if same else 0) + 1
    elif status in FINISHED:
        row["retry_count"] = 0
        row["processed_at"] = datetime.now(timezone.utc).isoformat()
    if result is not None:
        row["extraction_result"] = result  # jsonb 칸 — 문자열로 넣으면 JSON 문자열 하나로 저장된다
    db.table("processing_queue").upsert(row, on_conflict="video_id").execute()


# ── 처리 ──────────────────────────────────────────────────────────────

def _video_row(video: dict, rest_id: int, rest: dict) -> dict:
    return {
        "video_id": video["video_id"],
        "channel_id": video["channel_id"],
        "restaurant_id": rest_id,
        "title": video.get("title"),
        "thumbnail_url": video.get("thumbnail_url"),
        "rating": rest.get("rating"),
        "summary": rest.get("summary"),
        "is_ad": bool(rest.get("is_ad", False)),
        "timestamp_seconds": rest.get("timestamp_seconds"),
        "published_at": video.get("published_at"),
        "menu": rest.get("menu") or None,
        "price": rest.get("price") or None,
        "quote": rest.get("quote") or None,
        "why": rest.get("why") or None,
        "detail": rest.get("detail"),
    }


def _save(db, video: dict, place: dict, rest: dict, confident: bool, out: list):
    region, city = region_city(place.get("address"))
    row = {
        "name": place["name"],
        "address": place.get("address"),
        "lat": place.get("lat"),
        "lng": place.get("lng"),
        "category": rest.get("category") or place.get("category") or "기타",
        "region": place.get("region") or region,
        "city": city,
        "naver_place_id": place.get("naver_place_id"),
        # 확신 낮은 것만 사람이 본다. 그동안은 사이트에 안 보인다
        "needs_review": not confident,
        "is_visible": confident,
    }
    out.append({**row, "menu": rest.get("menu"), "price": rest.get("price"), "quote": rest.get("quote"), "detail": rest.get("detail")})
    if db is None:
        return
    from supabase_client import upsert_restaurant, upsert_video
    rid = upsert_restaurant(db, row)
    upsert_video(db, _video_row(video, rid, rest))


def drop_old_rows(db, vid: str) -> list[int]:
    """재추출 전 이 영상의 기존 videos 행을 지운다. 연결돼 있던 가게 id를 돌려준다.

    TRUNCATE 대신 영상 단위로 바꿔 끼운다 — 백필이 2~3주 걸리는 동안 사이트가 비지 않게.
    """
    if db is None:
        return []
    old = db.table("videos").select("restaurant_id").eq("video_id", vid).execute().data or []
    if old:
        db.table("videos").delete().eq("video_id", vid).execute()
    return [r["restaurant_id"] for r in old if r.get("restaurant_id")]


def hide_orphans(db, rest_ids: list[int]) -> None:
    """영상이 하나도 안 남은 가게는 숨긴다(옛 추출에만 있던 가게)."""
    for rid in set(rest_ids):
        left = db.table("videos").select("id").eq("restaurant_id", rid).limit(1).execute().data
        if not left:
            db.table("restaurants").update({"is_visible": False}).eq("id", rid).execute()


def process_video(db, video: dict, stats: dict) -> list[dict]:
    """영상 하나를 끝까지 처리한다. 저장한(또는 dry-run이면 저장할) 가게 목록을 돌려준다."""
    vid = video["video_id"]
    logger.info("처리: %s (%s)", video.get("title"), vid)
    saved: list[dict] = []
    transcript = fetch_transcript(vid)
    if not transcript:
        queue_set(db, video, "no_transcript")
        return saved

    restaurants = _cached_extract(vid)
    if restaurants is not None:
        logger.info("  저장해 둔 추출 결과를 쓴다")
    else:
        try:
            restaurants, usage = extract_restaurants(transcript, title=video.get("title", ""),
                                                     description=video.get("description", ""))
        except ExtractBlocked:
            raise
        except ExtractError as e:
            logger.warning("  추출 실패: %s", e)
            stats["failed"] += 1
            queue_set(db, video, "failed", error=str(e)[:500])
            return saved
        _keep_extract(vid, restaurants)
        stats["input_tokens"] += usage["input_tokens"]
        stats["output_tokens"] += usage["output_tokens"]
        USAGE_LOG.parent.mkdir(parents=True, exist_ok=True)
        with USAGE_LOG.open("a", encoding="utf-8") as f:
            f.write(json.dumps({"at": datetime.now().isoformat(timespec="seconds"), "video_id": vid,
                                "restaurants": len(restaurants), **usage}) + "\n")

    # 설명란 naver.me 링크 = 유튜버가 직접 적은 가게 → 이름이 맞으면 그 플레이스 정보를 쓴다(확신 high)
    desc_places = parse_description_places(video.get("description", ""))
    old_rest_ids = drop_old_rows(db, vid)

    for rest in restaurants:
        name = rest.get("name", "")
        if is_chain(name):
            log_skipped(video, rest, reason="chain_blacklist")
            stats["skipped"] += 1
            continue
        place = next((p for p in desc_places if name_similar(name, p.get("name", ""))), None)
        if place:
            place = {**place, "region": None}
            confident = True
        else:
            loc = search_restaurant(name, rest.get("address_hint", ""))
            stats["naver_calls"] += 1
            if not loc or loc.get("lat") is None:
                # 지역검색에 안 나온다 = 폐업했거나 이름이 틀렸다 → 저장하지 않는다
                log_skipped(video, rest, reason="naver_no_region_match")
                stats["skipped"] += 1
                continue
            if is_chain(loc.get("name", "")):
                log_skipped(video, rest, reason="chain_blacklist_naver_name")
                stats["skipped"] += 1
                continue
            place, confident = loc, loc.get("confidence") == "high"
        if place.get("naver_place_id") and get_place_status(place["naver_place_id"]) == "closed":
            log_skipped(video, rest, reason="closed")
            stats["closed"] += 1
            continue
        _save(db, video, place, rest, confident, saved)
        stats["restaurants"] += 1
        stats["needs_review"] += 0 if confident else 1

    if old_rest_ids:
        hide_orphans(db, old_rest_ids)
    queue_set(db, video, "done" if saved else "no_restaurant", result=restaurants)
    return saved


def trigger_revalidate() -> None:
    """mukmap.kr 캐시 무효화. 실패해도 파이프라인은 성공 처리."""
    base = os.environ.get("MUKMAP_BASE_URL")
    secret = os.environ.get("MUKMAP_REVALIDATE_SECRET")
    if not base or not secret:
        logger.info("revalidate 스킵: MUKMAP_BASE_URL / MUKMAP_REVALIDATE_SECRET 미설정")
        return
    try:
        import urllib.request
        req = urllib.request.Request(f"{base.rstrip('/')}/api/revalidate", method="POST",
                                     headers={"x-revalidate-secret": secret})
        with urllib.request.urlopen(req, timeout=10) as r:
            logger.info("revalidate 호출 성공: %s", r.status)
    except Exception as e:
        logger.warning("revalidate 호출 실패 (무시): %s", e)


def main():
    ap = argparse.ArgumentParser(description="MukMap 맛집 파이프라인")
    ap.add_argument("--max-videos", type=int, default=10)
    ap.add_argument("--max-minutes", type=int, default=50, help="회차 상한(분). 0 = 무제한")
    ap.add_argument("--video-id", help="이 영상 하나만")
    ap.add_argument("--dry-run", action="store_true", help="DB 쓰기 없이 결과 JSON만 출력")
    ap.add_argument("--workers", type=int, default=1, help="동시에 처리할 영상 수")
    args = ap.parse_args()

    load_env()
    from supabase_client import get_client
    db_read = get_client()
    db = None if args.dry_run else db_read
    youtube = build("youtube", "v3", developerKey=os.environ["YOUTUBE_API_KEY"])

    if args.video_id:
        ch = next((c for c in food_channels()
                   if (TRANSCRIPTS / c["slug"] / f"{args.video_id}.txt").exists()), None)
        if not ch:
            logger.error("자막 파일 없음: %s", args.video_id)
            sys.exit(1)
        todo = [{"video_id": args.video_id, "channel_id": ch["id"], "slug": ch["slug"], "published": ""}]
    else:
        todo = candidates(db_read, args.max_videos)
    logger.info("이번 회차 %d개 (prompt %s)", len(todo), PROMPT_VERSION)
    if not todo:
        return
    enrich_metadata(youtube, todo)

    stats = dict(videos=0, restaurants=0, needs_review=0, skipped=0, closed=0, failed=0,
                 naver_calls=0, input_tokens=0, output_tokens=0)
    deadline = time.time() + args.max_minutes * 60 if args.max_minutes else None
    results = {}
    counters = list(stats)  # stats["blocked"](문자열)가 끼어도 합산 키는 숫자만
    lock = threading.Lock()
    stop = threading.Event()
    local = threading.local()

    def client():
        if args.dry_run:
            return None
        if getattr(local, "db", None) is None:
            local.db = db if args.workers == 1 else get_client()
        return local.db

    def run_one(v):
        if stop.is_set() or (deadline and time.time() >= deadline):
            return
        mine = dict.fromkeys(counters, 0)
        try:
            for attempt in range(3):
                try:
                    res = process_video(client(), v, mine)
                    break
                except httpx.TransportError as e:
                    # Supabase HTTP/2 연결이 가끔 SSL 오류(bad record mac)로 끊긴다 — 연결을 새로 열고 같은 영상을 다시 한다
                    logger.warning("DB 연결 오류(%d/3): %s — %s", attempt + 1, v["video_id"], e)
                    time.sleep(5 * (attempt + 1))
                    local.db = None if args.dry_run else get_client()
            else:
                logger.error("DB 연결 오류 3회 — 이 영상은 건너뛰고 다음 회차에 다시 한다: %s", v["video_id"])
                mine["failed"] += 1
                res = None
        except ExtractBlocked as e:
            # 로그인 만료·한도 초과는 다음 영상도 똑같이 실패한다. 큐는 그대로 두고 다음 회차에 다시 한다
            logger.error("추출 중단(이번 회차 종료): %s", e)
            stop.set()
            with lock:
                stats["blocked"] = str(e)[:200]
            return
        except Exception:
            # 동시에 돌 때 같은 가게를 두 영상이 함께 넣으면 중복 키로 실패할 수 있다 — 다음 회차에 다시 한다
            logger.exception("영상 처리 실패 — 다음 회차에 다시 한다: %s", v["video_id"])
            mine["failed"] += 1
            res = None
        with lock:
            for k, n in mine.items():
                stats[k] += n
            if res is not None:
                results[v["video_id"]] = res
                stats["videos"] += 1

    if args.workers == 1:
        for v in todo:
            run_one(v)
            if stop.is_set() or (deadline and time.time() >= deadline):
                break
    else:
        # claude -p 추출이 영상당 수십 초라 여러 영상을 동시에 처리한다
        with ThreadPoolExecutor(max_workers=args.workers) as pool:
            list(pool.map(run_one, todo))
    if deadline and time.time() >= deadline:
        logger.info("회차 상한 도달 — 남은 영상은 다음 회차로")

    print(json.dumps(stats, ensure_ascii=False))
    if args.dry_run:
        print(json.dumps(results, ensure_ascii=False, indent=2))
    elif stats["restaurants"]:
        trigger_revalidate()


if __name__ == "__main__":
    main()

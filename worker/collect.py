#!/usr/bin/env python3
"""MukMap data collection script.

Usage:
    python worker/collect.py                    # full run
    python worker/collect.py --dry-run          # no DB writes
    python worker/collect.py --max-per-channel 5
    python worker/collect.py --cost-limit 0.5   # 누적 AI 비용 상한 (USD)
"""

import argparse
import json
import logging
import os
import random
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

from dotenv import load_dotenv
from googleapiclient.discovery import build

from transcript_fetcher import fetch_transcript
from restaurant_extractor import extract_restaurants
from naver_search import search_restaurant, REGION_MAP as _REGION_MAP
from chain_blacklist import is_chain
from description_parser import parse_description_places
from skip_logger import log_skipped

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

# Channels to collect from. rawdata/transcripts/{slug}와 매칭.
CHANNELS = [
    {"id": "UCehQiKylaW68H_OtRS36wGQ", "slug": "dulcinea_studio", "name": "둘시네아"},
    {"id": "UCfpaSruWW3S4dibonKXENjA", "slug": "tzuyang", "name": "쯔양"},
    {"id": "UCzgpOnor-MzT-1iflZil2GQ", "slug": "jaesunrang", "name": "재선랑"},
    {"id": "UC-OAmhcFgX9t_OF6fQ-4B1w", "slug": "kimjjamppong", "name": "김쨈뽕"},
    {"id": "UC-x55HF1-IilhxZOzwJm7JA", "slug": "kimsawon", "name": "김사원"},
]

_METADATA_PATH = Path(__file__).resolve().parent.parent / "rawdata" / "metadata.json"

# Claude Haiku pricing (per million tokens)
HAIKU_INPUT_PRICE = 0.80   # $/M input tokens
HAIKU_OUTPUT_PRICE = 4.00  # $/M output tokens

DEFAULT_MAX_AGE_DAYS = 30          # 기본 수집 기간 (일)
DEFAULT_COST_LIMIT_USD = 2.0       # 누적 AI 비용 상한 (USD)

def _region_from_address(address: str | None) -> str | None:
    if not address:
        return None
    for k, v in _REGION_MAP.items():
        if k in address:
            return v
    return None


def _build_video_row(video: dict, rest_id: int, rest: dict) -> dict:
    return {
        "video_id": video["video_id"],
        "channel_id": video["channel_id"],
        "restaurant_id": rest_id,
        "title": video.get("title"),
        "thumbnail_url": video.get("thumbnail_url"),
        "rating": rest.get("rating"),
        "summary": rest.get("summary"),
        "is_ad": rest.get("is_ad", False),
        "timestamp_seconds": rest.get("timestamp_seconds"),
        "published_at": video.get("published_at"),
    }


def _usd_cost(input_tokens: int, output_tokens: int) -> float:
    return (
        input_tokens * HAIKU_INPUT_PRICE / 1_000_000
        + output_tokens * HAIKU_OUTPUT_PRICE / 1_000_000
    )


def load_env():
    project_root = Path(__file__).resolve().parent.parent
    load_dotenv(project_root / ".env")
    load_dotenv(project_root / ".env.local", override=False)


def get_youtube_service():
    return build("youtube", "v3", developerKey=os.environ["YOUTUBE_API_KEY"])


def load_metadata() -> dict[str, dict]:
    """rawdata/metadata.json 로드. 없으면 에러."""
    if not _METADATA_PATH.exists():
        logger.error(
            "rawdata/metadata.json 없음. 먼저 `python scripts/fetch_metadata.py`를 실행하세요."
        )
        sys.exit(1)
    return json.loads(_METADATA_PATH.read_text(encoding="utf-8"))


def collect_candidate_videos(
    metadata: dict[str, dict],
    channel_ids: set[str],
    max_age_days: int,
    existing_ids: set[str],
    reprocess: bool,
) -> list[dict]:
    """metadata.json에서 조건 맞는 영상만 선별.

    - channel_id가 수집 대상 채널에 속하고
    - published_at이 최근 max_age_days 이내이고
    - reprocess가 아니면 processing_queue에 없는 것만
    """
    cutoff = (datetime.now(timezone.utc) - timedelta(days=max_age_days)).strftime(
        "%Y-%m-%dT%H:%M:%SZ"
    )
    out: list[dict] = []
    for vid, meta in metadata.items():
        if meta.get("channel_id") not in channel_ids:
            continue
        if (meta.get("published_at") or "") < cutoff:
            continue
        if not reprocess and vid in existing_ids:
            continue
        out.append({
            "video_id": vid,
            "title": meta.get("title", ""),
            "description": meta.get("description", ""),
            "thumbnail_url": meta.get("thumbnail_url"),
            "published_at": meta.get("published_at"),
            "channel_id": meta.get("channel_id"),
        })
    # 최신 영상부터 처리
    out.sort(key=lambda v: v["published_at"] or "", reverse=True)
    return out


def process_video(
    video: dict, dry_run: bool, db_client,
    reprocess: bool = False,
    cost_remaining_usd: float = float("inf"),
) -> dict:
    """Process a single video: description 우선 → AI fallback → DB/skip-log.

    Returns stats dict with desc_parsed, skipped, cost_limit_hit fields.
    """
    stats = {
        "restaurants_found": 0,
        "with_coords": 0,
        "needs_review": 0,
        "desc_parsed": 0,
        "skipped": 0,
        "input_tokens": 0,
        "output_tokens": 0,
        "naver_calls": 0,
        "cost_limit_hit": False,
    }

    video_id = video["video_id"]
    description = video.get("description", "") or ""
    logger.info("Processing: %s (%s)", video["title"], video_id)

    if not dry_run:
        from supabase_client import update_queue_status
        update_queue_status(db_client, video_id, "processing")

    # 1. description 우선 경로 (naver.me 파싱, AI 0원)
    desc_places = parse_description_places(description) if description else []
    if desc_places:
        logger.info("  description 파싱 %d곳 (AI 스킵)", len(desc_places))
        stats["restaurants_found"] = len(desc_places)
        stats["desc_parsed"] = len(desc_places)
        for place in desc_places:
            stats["with_coords"] += 1
            rest_data = {
                "name": place["name"],
                "address": place.get("address"),
                "lat": place.get("lat"),
                "lng": place.get("lng"),
                "category": place.get("category", "기타"),
                "region": _region_from_address(place.get("address")),
                "needs_review": False,
            }
            if dry_run:
                logger.info(
                    "  [DRY-RUN] %s | %s | (%s, %s)",
                    rest_data["name"], rest_data["address"],
                    rest_data["lat"], rest_data["lng"],
                )
            else:
                from supabase_client import upsert_restaurant, upsert_video
                rest_id = upsert_restaurant(db_client, rest_data)
                upsert_video(db_client, _build_video_row(video, rest_id, place))
        if not dry_run:
            update_queue_status(db_client, video_id, "done")
        return stats

    # 2. 비용 상한 체크 (AI 경로 진입 전)
    if cost_remaining_usd <= 0:
        logger.warning("  비용 상한 초과 → AI 스킵")
        stats["cost_limit_hit"] = True
        return stats

    # 3. AI fallback
    restaurants = None
    if reprocess and not dry_run:
        from supabase_client import get_cached_extraction
        cached = get_cached_extraction(db_client, video_id)
        if cached:
            logger.info("  Using cached extraction (%d restaurants)", len(cached))
            restaurants = cached

    if restaurants is None:
        transcript = fetch_transcript(video_id)
        if not transcript:
            logger.info("  No transcript available")
            if not dry_run:
                update_queue_status(db_client, video_id, "no_transcript")
            return stats

        restaurants, token_usage = extract_restaurants(
            transcript,
            title=video.get("title", ""),
            description=description,
        )
        stats["input_tokens"] = token_usage.get("input_tokens", 0)
        stats["output_tokens"] = token_usage.get("output_tokens", 0)

        if restaurants and not dry_run:
            from supabase_client import save_extraction_result
            save_extraction_result(db_client, video_id, restaurants)

    if not restaurants:
        logger.info("  No restaurants found in transcript")
        if not dry_run:
            update_queue_status(db_client, video_id, "no_restaurant")
        return stats

    stats["restaurants_found"] = len(restaurants)
    logger.info("  Found %d restaurants", len(restaurants))

    # 4. 각 맛집에 대해 네이버 검색 → 실패 시 DB 스킵 + JSONL 로그
    for rest in restaurants:
        # AI가 프롬프트 블랙리스트를 지키지 않고 체인점을 뽑은 경우 차단
        if is_chain(rest.get("name", "")):
            stats["skipped"] += 1
            log_skipped(video, rest, reason="chain_blacklist")
            logger.info("  체인점 스킵(AI): %s", rest.get("name"))
            continue

        location = search_restaurant(rest.get("name", ""), rest.get("address_hint", ""))
        stats["naver_calls"] += 1

        if not location or location.get("lat") is None:
            stats["skipped"] += 1
            log_skipped(video, rest, reason="naver_no_region_match")
            logger.info(
                "  스킵: %s (hint=%r)",
                rest.get("name"), rest.get("address_hint"),
            )
            continue

        # 네이버가 '롯데리아 면목중앙점'처럼 체인 지점명으로 교정 리턴하는 경우도 차단
        if is_chain(location.get("name", "")):
            stats["skipped"] += 1
            log_skipped(video, rest, reason="chain_blacklist_naver_name")
            logger.info("  체인점 스킵(네이버): %s", location.get("name"))
            continue

        stats["with_coords"] += 1
        rest_data = {
            "name": location.get("name", rest["name"]),
            "address": location.get("address"),
            "lat": location.get("lat"),
            "lng": location.get("lng"),
            "category": rest.get("category", "기타"),
            "region": location.get("region"),
            "needs_review": False,
        }
        if dry_run:
            logger.info(
                "  [DRY-RUN] %s (%s) lat=%s lng=%s",
                rest_data["name"], rest_data.get("region", "?"),
                rest_data.get("lat"), rest_data.get("lng"),
            )
        else:
            from supabase_client import upsert_restaurant, upsert_video
            rest_id = upsert_restaurant(db_client, rest_data)
            upsert_video(db_client, _build_video_row(video, rest_id, rest))

    if not dry_run:
        update_queue_status(db_client, video_id, "done")

    return stats


def _print_summary(total_stats: dict, aborted: bool = False, cost_limit: float = 0.0) -> None:
    input_cost = total_stats["input_tokens"] * HAIKU_INPUT_PRICE / 1_000_000
    output_cost = total_stats["output_tokens"] * HAIKU_OUTPUT_PRICE / 1_000_000
    total_cost = input_cost + output_cost
    print("\n=== 수집 결과 ===")
    if aborted:
        print(f"⚠️  비용 상한 ${cost_limit:.2f} 초과로 중단됨")
    print(f"처리 영상: {total_stats['videos_processed']}개")
    print(
        f"추출 맛집: {total_stats['restaurants_found']}개 "
        f"(좌표 있음: {total_stats['with_coords']}, "
        f"description 파싱: {total_stats.get('desc_parsed', 0)}, "
        f"네이버 매칭 실패 스킵: {total_stats.get('skipped', 0)}, "
        f"보정 필요: {total_stats['needs_review']})"
    )
    print(
        f"Claude Haiku: input {total_stats['input_tokens']} tokens, "
        f"output {total_stats['output_tokens']} tokens (${total_cost:.4f})"
    )
    print(f"네이버 검색: {total_stats['naver_calls']}회")
    print(f"YouTube API: {total_stats['youtube_units']} units")
    if total_stats.get("skipped"):
        print(f"→ 스킵된 가게 확인: rawdata/skipped/")


def main():
    parser = argparse.ArgumentParser(description="MukMap data collector")
    parser.add_argument("--max-per-channel", type=int, default=10)
    parser.add_argument("--dry-run", action="store_true", help="No DB writes")
    parser.add_argument("--reprocess", action="store_true", help="캐시된 추출 결과로 좌표만 재검색")
    parser.add_argument("--channel", type=str, help="특정 채널만 수집 (이름, 예: 둘시네아)")
    parser.add_argument("--video-id", type=str, help="특정 영상 하나만 처리 (video ID)")
    parser.add_argument(
        "--cost-limit", type=float, default=DEFAULT_COST_LIMIT_USD,
        help=f"누적 Haiku 비용 상한 USD (기본 {DEFAULT_COST_LIMIT_USD}). 초과 시 AI 호출 중단",
    )
    parser.add_argument(
        "--max-age-days", type=int, default=DEFAULT_MAX_AGE_DAYS,
        help=f"published_at 기준 최근 N일 이내만 처리 (기본 {DEFAULT_MAX_AGE_DAYS})",
    )
    args = parser.parse_args()

    load_env()

    required = ["YOUTUBE_API_KEY", "ANTHROPIC_API_KEY", "NAVER_SEARCH_CLIENT_ID", "NAVER_SEARCH_CLIENT_SECRET"]
    if not args.dry_run:
        required += ["SUPABASE_URL", "SUPABASE_SERVICE_KEY"]
    missing = [k for k in required if not os.environ.get(k)]
    if missing:
        logger.error("Missing env vars: %s", ", ".join(missing))
        sys.exit(1)

    db_client = None
    existing_ids: set[str] = set()
    if not args.dry_run:
        from supabase_client import get_client, get_existing_video_ids, insert_to_queue
        db_client = get_client()
        existing_ids = get_existing_video_ids(db_client)

    youtube = get_youtube_service()

    total_stats = {
        "videos_processed": 0,
        "restaurants_found": 0,
        "with_coords": 0,
        "needs_review": 0,
        "desc_parsed": 0,
        "skipped": 0,
        "cost_limit_hit_count": 0,
        "input_tokens": 0,
        "output_tokens": 0,
        "naver_calls": 0,
        "youtube_units": 0,
    }
    aborted = False

    # --video-id: 단일 영상
    if args.video_id:
        video = {"video_id": args.video_id, "title": "", "description": "",
                 "channel_id": "", "thumbnail_url": "", "published_at": None}
        try:
            resp = youtube.videos().list(part="snippet", id=args.video_id).execute()
            if resp.get("items"):
                snippet = resp["items"][0]["snippet"]
                video["title"] = snippet["title"]
                video["description"] = snippet.get("description", "")
                video["channel_id"] = snippet["channelId"]
                video["thumbnail_url"] = snippet.get("thumbnails", {}).get("medium", {}).get("url")
                video["published_at"] = snippet.get("publishedAt")
        except Exception as e:
            logger.error("YouTube API error: %s", e)

        logger.info("Processing single video: %s (%s)", video["title"], args.video_id)
        total_stats["youtube_units"] += 1

        if not args.dry_run:
            insert_to_queue(db_client, args.video_id, video["channel_id"])

        remaining = args.cost_limit
        stats = process_video(video, args.dry_run, db_client,
                              reprocess=args.reprocess,
                              cost_remaining_usd=remaining)
        total_stats["videos_processed"] += 1
        for k in ("restaurants_found", "with_coords", "needs_review",
                  "desc_parsed", "skipped", "input_tokens", "output_tokens", "naver_calls"):
            total_stats[k] += stats.get(k, 0)
        _print_summary(total_stats, aborted=False, cost_limit=args.cost_limit)
        return

    # 1. rawdata/metadata.json 기반 수집 대상 선별
    channels = CHANNELS
    if args.channel:
        channels = [c for c in CHANNELS if args.channel.lower() in c["name"].lower()]
        if not channels:
            logger.error("채널 '%s'을 찾을 수 없습니다. 가능한 채널: %s",
                         args.channel, ", ".join(c["name"] for c in CHANNELS))
            sys.exit(1)

    metadata = load_metadata()
    channel_id_set = {c["id"] for c in channels}
    all_new_videos = collect_candidate_videos(
        metadata=metadata,
        channel_ids=channel_id_set,
        max_age_days=args.max_age_days,
        existing_ids=existing_ids,
        reprocess=args.reprocess,
    )
    logger.info(
        "수집 대상: %d영상 (metadata %d개 중 최근 %d일, 채널 %d개 필터)",
        len(all_new_videos), len(metadata), args.max_age_days, len(channels),
    )

    if not args.dry_run and not args.reprocess and all_new_videos:
        for v in all_new_videos:
            insert_to_queue(db_client, v["video_id"], v["channel_id"])

    # 2. Process videos (with cost-limit check)
    for i, video in enumerate(all_new_videos):
        spent = _usd_cost(total_stats["input_tokens"], total_stats["output_tokens"])
        remaining = args.cost_limit - spent
        if remaining <= 0:
            logger.warning("누적 비용 $%.4f >= 상한 $%.2f → 중단", spent, args.cost_limit)
            aborted = True
            break

        stats = process_video(video, args.dry_run, db_client,
                              reprocess=args.reprocess,
                              cost_remaining_usd=remaining)
        total_stats["videos_processed"] += 1
        for k in ("restaurants_found", "with_coords", "needs_review",
                  "desc_parsed", "skipped", "input_tokens", "output_tokens", "naver_calls"):
            total_stats[k] += stats.get(k, 0)
        if stats.get("cost_limit_hit"):
            total_stats["cost_limit_hit_count"] += 1

        if i < len(all_new_videos) - 1:
            delay = random.uniform(8, 15)
            logger.debug("Sleeping %.1fs", delay)
            time.sleep(delay)

    _print_summary(total_stats, aborted=aborted, cost_limit=args.cost_limit)

    if args.dry_run:
        print("\n[DRY-RUN 모드] DB 저장 없음")
    elif total_stats["videos_processed"] > 0:
        trigger_revalidate()


def trigger_revalidate() -> None:
    """수집 후 mukmap.kr 캐시 무효화. 실패해도 워커는 성공 처리."""
    base = os.environ.get("MUKMAP_BASE_URL")
    secret = os.environ.get("REVALIDATE_SECRET")
    if not base or not secret:
        logger.info("revalidate 스킵: MUKMAP_BASE_URL / REVALIDATE_SECRET 미설정")
        return
    try:
        import urllib.request
        req = urllib.request.Request(
            f"{base.rstrip('/')}/api/revalidate",
            method="POST",
            headers={"x-revalidate-secret": secret},
        )
        with urllib.request.urlopen(req, timeout=10) as r:
            logger.info("revalidate 호출 성공: %s", r.status)
    except Exception as e:
        logger.warning("revalidate 호출 실패 (무시): %s", e)


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""MukMap cron job entry point for GitHub Actions.

Unlike collect.py (local/manual), this reads env vars directly from
os.environ (injected by GitHub Actions secrets).
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

# Add worker dir to path for sibling imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from googleapiclient.discovery import build

from transcript_fetcher import fetch_transcript
from restaurant_extractor import extract_restaurants
from naver_search import search_restaurant, REGION_MAP as _REGION_MAP
from chain_blacklist import is_chain
from description_parser import parse_description_places
from skip_logger import log_skipped
from supabase_client import (
    get_client,
    get_existing_video_ids,
    insert_to_queue,
    update_queue_status,
    upsert_restaurant,
    upsert_video,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

CHANNELS = [
    {"id": "UCehQiKylaW68H_OtRS36wGQ", "slug": "dulcinea_studio", "name": "둘시네아"},
    {"id": "UCfpaSruWW3S4dibonKXENjA", "slug": "tzuyang", "name": "쯔양"},
    {"id": "UCzgpOnor-MzT-1iflZil2GQ", "slug": "jaesunrang", "name": "재선랑"},
    {"id": "UC-OAmhcFgX9t_OF6fQ-4B1w", "slug": "kimjjamppong", "name": "김쨈뽕"},
    {"id": "UC-x55HF1-IilhxZOzwJm7JA", "slug": "kimsawon", "name": "김사원"},
]

HAIKU_INPUT_PRICE = 0.80
HAIKU_OUTPUT_PRICE = 4.00
DEFAULT_MAX_AGE_DAYS = 30
DEFAULT_COST_LIMIT_USD = 2.0

_METADATA_PATH = Path(__file__).resolve().parent.parent / "rawdata" / "metadata.json"


def load_metadata() -> dict[str, dict]:
    if not _METADATA_PATH.exists():
        logger.error("rawdata/metadata.json 없음. scripts/fetch_metadata.py 먼저 실행.")
        sys.exit(1)
    return json.loads(_METADATA_PATH.read_text(encoding="utf-8"))


def collect_candidate_videos(
    metadata: dict[str, dict],
    channel_ids: set[str],
    max_age_days: int,
    existing_ids: set[str],
) -> list[dict]:
    cutoff = (datetime.now(timezone.utc) - timedelta(days=max_age_days)).strftime(
        "%Y-%m-%dT%H:%M:%SZ"
    )
    out: list[dict] = []
    for vid, meta in metadata.items():
        if meta.get("channel_id") not in channel_ids:
            continue
        if (meta.get("published_at") or "") < cutoff:
            continue
        if vid in existing_ids:
            continue
        out.append({
            "video_id": vid,
            "title": meta.get("title", ""),
            "description": meta.get("description", ""),
            "thumbnail_url": meta.get("thumbnail_url"),
            "published_at": meta.get("published_at"),
            "channel_id": meta.get("channel_id"),
        })
    out.sort(key=lambda v: v["published_at"] or "", reverse=True)
    return out

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


def process_video(video: dict, db_client, cost_remaining_usd: float = float("inf")) -> dict:
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
    update_queue_status(db_client, video_id, "processing")

    # 1. description 우선 (AI 0원)
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
            rest_id = upsert_restaurant(db_client, rest_data)
            upsert_video(db_client, _build_video_row(video, rest_id, place))
        update_queue_status(db_client, video_id, "done")
        return stats

    # 2. 비용 상한
    if cost_remaining_usd <= 0:
        logger.warning("  비용 상한 초과 → AI 스킵")
        stats["cost_limit_hit"] = True
        return stats

    # 3. AI fallback
    transcript = fetch_transcript(video_id)
    if not transcript:
        logger.info("  No transcript")
        update_queue_status(db_client, video_id, "no_transcript")
        return stats

    # ★ 버그 수정: 기존 lines 74에서 title/description 누락
    restaurants, token_usage = extract_restaurants(
        transcript,
        title=video.get("title", ""),
        description=description,
    )
    stats["input_tokens"] = token_usage.get("input_tokens", 0)
    stats["output_tokens"] = token_usage.get("output_tokens", 0)

    if not restaurants:
        logger.info("  No restaurants found")
        update_queue_status(db_client, video_id, "no_restaurant")
        return stats

    stats["restaurants_found"] = len(restaurants)
    logger.info("  Found %d restaurants", len(restaurants))

    # 4. Naver search → 실패 시 DB 스킵 + JSONL
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
            logger.info("  스킵: %s (hint=%r)", rest.get("name"), rest.get("address_hint"))
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
        rest_id = upsert_restaurant(db_client, rest_data)
        upsert_video(db_client, _build_video_row(video, rest_id, rest))

    update_queue_status(db_client, video_id, "done")
    return stats


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--video-id", type=str, help="특정 영상 하나만 처리")
    parser.add_argument(
        "--cost-limit", type=float, default=DEFAULT_COST_LIMIT_USD,
        help=f"누적 Haiku 비용 상한 USD (기본 {DEFAULT_COST_LIMIT_USD}). 초과 시 AI 호출 중단",
    )
    args = parser.parse_args()

    required = [
        "SUPABASE_URL", "SUPABASE_SERVICE_KEY", "YOUTUBE_API_KEY",
        "ANTHROPIC_API_KEY", "NAVER_SEARCH_CLIENT_ID", "NAVER_SEARCH_CLIENT_SECRET",
    ]
    missing = [k for k in required if not os.environ.get(k)]
    if missing:
        logger.error("Missing env vars: %s", ", ".join(missing))
        sys.exit(1)

    db_client = get_client()
    youtube = build("youtube", "v3", developerKey=os.environ["YOUTUBE_API_KEY"])
    existing_ids = get_existing_video_ids(db_client)

    totals = {
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

    all_new_videos = []

    # --video-id: 단일 영상
    if args.video_id:
        video = {"video_id": args.video_id, "title": "", "description": "", "channel_id": ""}
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
        insert_to_queue(db_client, args.video_id, video["channel_id"])
        stats = process_video(video, db_client, cost_remaining_usd=args.cost_limit)
        totals["videos_processed"] += 1
        for k in ("restaurants_found", "with_coords", "needs_review",
                  "desc_parsed", "skipped", "input_tokens", "output_tokens", "naver_calls"):
            totals[k] += stats.get(k, 0)

        input_cost = totals["input_tokens"] * HAIKU_INPUT_PRICE / 1_000_000
        output_cost = totals["output_tokens"] * HAIKU_OUTPUT_PRICE / 1_000_000
        print(
            f"\n=== 수집 결과 ===\n"
            f"처리 영상: 1개\n"
            f"추출 맛집: {totals['restaurants_found']}개 "
            f"(description 파싱: {totals['desc_parsed']}, 스킵: {totals['skipped']})\n"
            f"Claude Haiku: ${input_cost + output_cost:.3f}"
        )
        return

    # 1. rawdata/metadata.json 기반 수집 대상 선별
    metadata = load_metadata()
    channel_id_set = {c["id"] for c in CHANNELS}
    all_new_videos = collect_candidate_videos(
        metadata=metadata,
        channel_ids=channel_id_set,
        max_age_days=DEFAULT_MAX_AGE_DAYS,
        existing_ids=existing_ids,
    )
    logger.info(
        "수집 대상: %d영상 (metadata %d개 중 최근 %d일)",
        len(all_new_videos), len(metadata), DEFAULT_MAX_AGE_DAYS,
    )
    if all_new_videos:
        for v in all_new_videos:
            insert_to_queue(db_client, v["video_id"], v["channel_id"])

    # 2. Process videos (with cost-limit)
    for i, video in enumerate(all_new_videos):
        spent = _usd_cost(totals["input_tokens"], totals["output_tokens"])
        remaining = args.cost_limit - spent
        if remaining <= 0:
            logger.warning("누적 비용 $%.4f >= 상한 $%.2f → 중단", spent, args.cost_limit)
            aborted = True
            break

        try:
            stats = process_video(video, db_client, cost_remaining_usd=remaining)
            totals["videos_processed"] += 1
            for k in ("restaurants_found", "with_coords", "needs_review",
                      "desc_parsed", "skipped", "input_tokens", "output_tokens", "naver_calls"):
                totals[k] += stats.get(k, 0)
            if stats.get("cost_limit_hit"):
                totals["cost_limit_hit_count"] += 1
        except Exception as e:
            logger.error("Failed to process %s: %s", video["video_id"], e)
            try:
                update_queue_status(db_client, video["video_id"], "failed", str(e))
            except Exception:
                pass

        if i < len(all_new_videos) - 1:
            time.sleep(random.uniform(2, 5))

    # Summary
    input_cost = totals["input_tokens"] * HAIKU_INPUT_PRICE / 1_000_000
    output_cost = totals["output_tokens"] * HAIKU_OUTPUT_PRICE / 1_000_000
    total_cost = input_cost + output_cost

    print("\n=== 수집 결과 ===")
    if aborted:
        print(f"⚠️  비용 상한 ${args.cost_limit:.2f} 초과로 중단됨")
    print(f"처리 영상: {totals['videos_processed']}개")
    print(
        f"추출 맛집: {totals['restaurants_found']}개 "
        f"(좌표 있음: {totals['with_coords']}, "
        f"description 파싱: {totals['desc_parsed']}, "
        f"네이버 매칭 실패 스킵: {totals['skipped']}, "
        f"보정 필요: {totals['needs_review']})"
    )
    print(
        f"Claude Haiku: input {totals['input_tokens']} tokens, "
        f"output {totals['output_tokens']} tokens (${total_cost:.3f})"
    )
    print(f"네이버 검색: {totals['naver_calls']}회")
    print(f"YouTube API: {totals['youtube_units']} units")
    if totals["skipped"]:
        print(f"→ 스킵된 가게 확인: rawdata/skipped/")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        logger.error("Cron job failed: %s", e)
        # Exit 0 to prevent cron failure alerts
        sys.exit(0)

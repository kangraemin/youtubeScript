#!/usr/bin/env python3
"""Fill channel thumbnail_url in Supabase channels table from YouTube API."""

import logging
import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from googleapiclient.discovery import build

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from supabase_client import get_client

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

CHANNELS = [
    "UCehQiKylaW68H_OtRS36wGQ",  # 둘시네아
    "UCyn-K7rZLXjGl7VXGweIlcA",  # 백종원
    "UCl23-Cci_SMqyGXE1T_LYUg",  # 성시경 먹을텐데
    "UCfpaSruWW3S4dibonKXENjA",  # 쯔양
    "UCA6KBBX8cLwYZNepxlE_7SA",  # 히밥
]


def main():
    project_root = Path(__file__).resolve().parent.parent
    load_dotenv(project_root / ".env")
    load_dotenv(project_root / ".env.local", override=False)

    youtube = build("youtube", "v3", developerKey=os.environ["YOUTUBE_API_KEY"])
    db = get_client()

    response = youtube.channels().list(
        part="snippet",
        id=",".join(CHANNELS),
    ).execute()

    for item in response.get("items", []):
        channel_id = item["id"]
        thumbnail_url = (
            item["snippet"]
            .get("thumbnails", {})
            .get("high", {})
            .get("url")
        )

        if not thumbnail_url:
            logger.warning("No thumbnail for %s", channel_id)
            continue

        result = (
            db.table("channels")
            .update({"thumbnail_url": thumbnail_url})
            .eq("id", channel_id)
            .execute()
        )
        logger.info("Updated %s: %s", channel_id, thumbnail_url)

    logger.info("Done. %d channels processed.", len(response.get("items", [])))


if __name__ == "__main__":
    main()

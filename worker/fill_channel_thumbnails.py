#!/usr/bin/env python3
"""channels 테이블을 channel_config의 먹방 채널과 맞춘다(id·이름·URL용 slug·썸네일)."""

import logging
import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from googleapiclient.discovery import build

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from supabase_client import get_client
from scripts.channel_config import food_channels

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)



def main():
    project_root = Path(__file__).resolve().parent.parent
    load_dotenv(project_root / ".env")
    load_dotenv(project_root / ".env.local", override=False)

    youtube = build("youtube", "v3", developerKey=os.environ["YOUTUBE_API_KEY"])
    db = get_client()

    response = youtube.channels().list(
        part="snippet",
        id=",".join(ch["id"] for ch in food_channels()),
    ).execute()

    thumbs = {
        it["id"]: it["snippet"].get("thumbnails", {}).get("high", {}).get("url")
        for it in response.get("items", [])
    }
    for ch in food_channels():
        # slug는 웹 주소(/youtuber/쯔양)에 그대로 쓰는 한글 이름이다
        row = {"id": ch["id"], "name": ch["name"], "slug": ch["name"]}
        if thumbs.get(ch["id"]):
            row["thumbnail_url"] = thumbs[ch["id"]]
        else:
            logger.warning("No thumbnail for %s", ch["id"])
        db.table("channels").upsert(row, on_conflict="id").execute()
        logger.info("Synced %s (%s)", ch["name"], ch["id"])

    logger.info("Done. %d channels processed.", len(response.get("items", [])))


if __name__ == "__main__":
    main()

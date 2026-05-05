"""AI 추출 후 네이버 매칭에 실패한 가게를 별도 JSONL로 남긴다.

`rawdata/skipped/YYYY-MM-DD.jsonl`에 한 줄씩 append. 사용자가 나중에 수동 검토/보정할 때 참조.
DB에는 삽입하지 않아 잘못된 좌표 오염을 방지한다.
"""
import json
import logging
from datetime import datetime, timezone
from pathlib import Path

logger = logging.getLogger(__name__)

_SKIP_DIR = Path(__file__).resolve().parent.parent / "rawdata" / "skipped"


def log_skipped(video: dict, extracted: dict, reason: str) -> None:
    """AI가 추출했으나 네이버 지역 매칭 실패한 엔트리를 오늘자 JSONL에 append."""
    _SKIP_DIR.mkdir(parents=True, exist_ok=True)
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    path = _SKIP_DIR / f"{today}.jsonl"
    entry = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "video_id": video.get("video_id"),
        "channel_id": video.get("channel_id"),
        "title": video.get("title"),
        "extracted": {
            "name": extracted.get("name"),
            "address_hint": extracted.get("address_hint"),
            "category": extracted.get("category"),
            "rating": extracted.get("rating"),
        },
        "reason": reason,
    }
    try:
        with path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    except Exception as e:
        logger.warning("skip_logger write failed: %s", e)

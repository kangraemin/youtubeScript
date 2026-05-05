"""로컬 자막 로더.

rawdata/transcripts/*/{video_id}.txt 를 읽어 segments로 파싱한다.
파일 없으면 None 반환 — 파이프라인은 description(naver.me)으로 fallback.
"""
import logging
import re
from pathlib import Path

logger = logging.getLogger(__name__)

_TS_LINE = re.compile(r"^(\d+):(\d+)\s*(.*)$")
_RAWDATA_DIR = Path(__file__).resolve().parent.parent / "rawdata" / "transcripts"


def fetch_transcript(video_id: str) -> list[dict] | None:
    """rawdata/transcripts/*/{video_id}.txt → [{"start": float, "text": str}]."""
    matches = list(_RAWDATA_DIR.glob(f"*/{video_id}.txt"))
    if not matches:
        logger.info("로컬 자막 없음: %s", video_id)
        return None
    path = matches[0]
    lines = path.read_text(encoding="utf-8").splitlines()
    segs: list[dict] = []
    for line in lines[2:]:  # 제목/URL 스킵
        s = line.strip()
        if not s:
            continue
        m = _TS_LINE.match(s)
        if not m:
            if segs:
                segs[-1]["text"] += " " + s
            continue
        mm, ss, rest = m.group(1), m.group(2), m.group(3)
        segs.append({"start": float(int(mm) * 60 + int(ss)), "text": rest.strip()})
    if segs:
        logger.info(
            "로컬 자막 사용: %s (%d segments, %s)",
            video_id, len(segs), path.name,
        )
    return segs if segs else None

"""YouTube description에 박힌 naver.me 단축링크를 네이버 플레이스 정보로 변환.

유튜버가 description에 `[식당정보] 가게명 https://naver.me/XXX` 식으로 정리해둔 경우
이걸 파싱하면 AI 호출 없이 공식 네이버 플레이스 좌표/주소를 바로 얻을 수 있다.
"""
import logging
import re
import time

import requests

from chain_blacklist import is_chain
from closure_check import fetch_place

logger = logging.getLogger(__name__)

NAVER_ME = re.compile(r"https?://naver\.me/[A-Za-z0-9]+")
UA = {"User-Agent": "Mozilla/5.0", "Referer": "https://map.naver.com/"}

def _resolve_shortlink(url: str) -> str | None:
    """`https://naver.me/XXX` → `map.naver.com/.../place/{place_id}` 리다이렉트 추적."""
    try:
        r = requests.get(url, allow_redirects=True, timeout=5, headers=UA)
        m = re.search(r"/place/(\d+)", r.url)
        return m.group(1) if m else None
    except Exception as e:
        logger.warning("naver.me resolve failed %s: %s", url, e)
        return None


def parse_description_places(description: str) -> list[dict]:
    """description의 naver.me 링크를 네이버 플레이스 정보 list로 변환. 체인점은 스킵.

    빈 리스트 반환 시 호출측이 AI 추출로 fallback해야 한다.
    """
    if not description:
        return []
    seen: set[str] = set()
    out: list[dict] = []
    for link in NAVER_ME.findall(description):
        if link in seen:
            continue
        seen.add(link)
        pid = _resolve_shortlink(link)
        if not pid:
            continue
        # 예전 map.naver.com/v5/api/place/summary는 301만 준다(2026-10-19) → 모바일 플레이스 페이지로 읽는다
        info = fetch_place(pid)
        if not info or info.get("lat") is None:
            if info and info.get("status") == "closed":
                logger.info("description 폐업/없는 가게 스킵: %s", pid)
            continue
        if info.get("status") == "closed":
            logger.info("description 폐업 가게 스킵: %s", info.get("name"))
            continue
        if is_chain(info.get("name", "")):
            logger.info("description 체인점 스킵: %s", info.get("name"))
            continue
        out.append(info)
        time.sleep(0.25)
    return out

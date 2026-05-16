"""채널 분류 — 요약 대상 / 제외 대상 + 카테고리별 크롤 정책.

다른 스크립트들이 import해서 사용한다:
    from scripts.channel_config import STOCK_ECON_SLUGS, policy_for, category_of

새 카테고리 추가 절차:
1. 슬러그 리스트(예: NEWS_SLUGS) 정의
2. CATEGORY_POLICY에 한 줄 추가 (예: "news": {"days": 14, "summary": True})
3. category_of()에 분기 추가
"""

# 주식·경제 채널 (요약 대상)
STOCK_ECON_SLUGS = [
    "moneycomics_videos",
    "shukaworld",
    "yonhap_economy",
    "jisik_inside",
    "developmong",
    "doniggangpae",
]

# 식당/먹방 채널 (요약 제외)
FOOD_SLUGS = [
    "dulcinea_studio",
    "tzuyang",
    "jaesunrang",
    "kimjjamppong",
    "kimsawon",
]

# 영상 너무 많은 별도 채널 (요약 제외, 수집은 함)
HEAVY_SLUGS = ["sampro_tv"]

# 요약 제외 집합 (기존 호환)
EXCLUDED_FROM_SUMMARY = set(FOOD_SLUGS) | set(HEAVY_SLUGS)


# === 카테고리 정책 ===
# 미래 정책(workers, max_videos 등)도 같은 dict에 추가 가능
CATEGORY_POLICY = {
    "stock_econ": {"days": 30, "summary": True},
    "food":       {"days": 60, "summary": False},
    "heavy":      {"days": 60, "summary": False},  # sampro_tv 등
}

DEFAULT_POLICY = {"days": 30, "summary": False}


def category_of(slug: str) -> str:
    """slug → 카테고리. 새 카테고리 추가 시 분기 추가."""
    if slug in STOCK_ECON_SLUGS:
        return "stock_econ"
    if slug in FOOD_SLUGS:
        return "food"
    if slug in HEAVY_SLUGS:
        return "heavy"
    return "other"


def policy_for(slug: str) -> dict:
    """slug → 정책 dict ({days, summary, ...}). 미등록 카테고리는 DEFAULT_POLICY."""
    return CATEGORY_POLICY.get(category_of(slug), DEFAULT_POLICY)

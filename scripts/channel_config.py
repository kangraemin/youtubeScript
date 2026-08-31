"""채널 분류 — 요약 대상 / 제외 대상 + 카테고리별 크롤 정책.

다른 스크립트들이 import해서 사용한다:
    from scripts.channel_config import SUMMARY_SLUGS, policy_for, category_of

새 카테고리 추가 절차:
1. 슬러그 리스트(예: NEWS_SLUGS) 정의
2. CATEGORY_POLICY에 한 줄 추가 (예: "news": {"days": 30, "summary": True, "min_duration_sec": 180})
3. category_of()에 분기 추가
4. 요약 대상이면 SUMMARY_SLUGS 합집합에 추가
"""

# 주식·경제 채널 (요약 대상, 쇼츠 필터 없음)
STOCK_ECON_SLUGS = [
    "moneycomics",
    "shukaworld",
    "jisik_inside",
    "developmong",
    "doniggangpae",
    # 머니코믹스에서 분리 독립. 매일 아침 "당일전략"이 9~19분이라 쇼츠 필터를 걸면 핵심이 날아간다
    # (최근 100편 실측: 3분 미만 9%, 3~20분 26% 중 22편이 당일전략).
    "alsangmoo",
]

# 뉴스 채널 (요약 대상, 단 쇼츠 제외 — 본방만)
NEWS_SLUGS = ["yonhap_economy"]

# 투자 미디어 채널 (요약 대상, 쇼츠 제외 — 영상+라이브만)
# 위폴은 머니코믹스 아침방송[바이킹스]이 분리된 채널. 최근 100편 실측에서 3분 미만이 30%인데
# 3~20분 구간은 0편 — 쇼츠(0:22~1:21)와 본방(36~76분)으로 딱 갈려 180초 컷이 본방을 건드리지 않는다.
INVEST_MEDIA_SLUGS = ["mk_wallstreet", "aspim_research", "wepoll"]

# 교양 채널 (요약 대상, 쇼츠 제외 — 동영상만)
CULTURE_SLUGS = ["sbs_gyoyangi"]

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

# 요약 큐 대상 = summary:True 카테고리 슬러그 합집합
SUMMARY_SLUGS = STOCK_ECON_SLUGS + NEWS_SLUGS + INVEST_MEDIA_SLUGS + CULTURE_SLUGS

# 요약 전 LLM 관련성 스크리닝을 적용할 채널 (비경제 콘텐츠가 섞인 채널만).
# 워커가 제목+앞부분으로 주식·경제 요약 가치를 판정해, 가치 없으면 screened_out 처리한다.
SCREEN_SLUGS = {"jisik_inside", "yonhap_economy"}


# === 카테고리 정책 ===
# 미래 정책(workers, max_videos 등)도 같은 dict에 추가 가능
# min_duration_sec > 0 이면 크롤 시 그 길이 미만 영상(쇼츠/단편) 제외
CATEGORY_POLICY = {
    "stock_econ":   {"days": 30, "summary": True,  "min_duration_sec": 0},
    "news":         {"days": 30, "summary": True,  "min_duration_sec": 180},
    "invest_media": {"days": 30, "summary": True,  "min_duration_sec": 180},
    "culture":      {"days": 30, "summary": True,  "min_duration_sec": 180},
    "food":         {"days": 60, "summary": False, "min_duration_sec": 0},
    "heavy":        {"days": 60, "summary": False, "min_duration_sec": 0},  # sampro_tv 등
}

DEFAULT_POLICY = {"days": 30, "summary": False, "min_duration_sec": 0}


def category_of(slug: str) -> str:
    """slug → 카테고리. 새 카테고리 추가 시 분기 추가."""
    if slug in STOCK_ECON_SLUGS:
        return "stock_econ"
    if slug in NEWS_SLUGS:
        return "news"
    if slug in INVEST_MEDIA_SLUGS:
        return "invest_media"
    if slug in CULTURE_SLUGS:
        return "culture"
    if slug in FOOD_SLUGS:
        return "food"
    if slug in HEAVY_SLUGS:
        return "heavy"
    return "other"


def policy_for(slug: str) -> dict:
    """slug → 정책 dict ({days, summary, min_duration_sec}). 미등록은 DEFAULT_POLICY."""
    return CATEGORY_POLICY.get(category_of(slug), DEFAULT_POLICY)

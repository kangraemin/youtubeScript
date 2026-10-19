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
    "heebab",
    "sungsikyung",
    "chureupkyeon",
]

# 영상 너무 많은 별도 채널 (요약 제외, 수집은 함)
HEAVY_SLUGS = ["sampro_tv"]

# 요약 제외 집합 (기존 호환)
EXCLUDED_FROM_SUMMARY = set(FOOD_SLUGS) | set(HEAVY_SLUGS)

# 요약 큐 대상 = summary:True 카테고리 슬러그 합집합
SUMMARY_SLUGS = STOCK_ECON_SLUGS + NEWS_SLUGS + INVEST_MEDIA_SLUGS + CULTURE_SLUGS

# 요약 전 LLM 관련성 스크리닝을 적용할 채널 (비경제 콘텐츠가 섞인 채널만).
# 워커가 제목+앞부분으로 주식·경제 요약 가치를 판정해, 가치 없으면 screened_out 처리한다.
# moneycomics: 콩트·상황극(「대표랑 외모로 싸우는 직원」 등)이 섞여 요약 피드에 노출됐다(2026-10-08).
SCREEN_SLUGS = {"jisik_inside", "yonhap_economy", "moneycomics"}


# === 채널 정의 (크롤러·get_transcript·mukmap 파이프라인이 공유) ===
# title_include: 제목에 이 문자열이 있는 영상만 목록에 넣는다.
CHANNELS = [
    {"id": "UCehQiKylaW68H_OtRS36wGQ", "slug": "dulcinea_studio",   "name": "둘시네아",            "tab": "videos"},
    {"id": "UCfpaSruWW3S4dibonKXENjA", "slug": "tzuyang",            "name": "쯔양",               "tab": "videos"},
    {"id": "UCzgpOnor-MzT-1iflZil2GQ", "slug": "jaesunrang",         "name": "재선랑",             "tab": "videos"},
    {"id": "UC-OAmhcFgX9t_OF6fQ-4B1w", "slug": "kimjjamppong",       "name": "김쨈뽕",            "tab": "videos"},
    {"id": "UC-x55HF1-IilhxZOzwJm7JA", "slug": "kimsawon",           "name": "김사원",             "tab": "videos"},
    {"id": "UCJo6G1u0e_-wS-JQn3T-zEw", "slug": "moneycomics",        "name": "머니코믹스",         "tab": "videos"},
    {"id": "UCsJ6RuBiTVWRX156FVbeaGg", "slug": "shukaworld",         "name": "슈카월드",           "tab": "videos", "handle": "syukaworld"},
    {"id": "UChlv4GSd7OQl3js-jkLOnFA", "slug": "sampro_tv",          "name": "삼프로TV",           "tab": "videos"},
    {"id": "UCA_hgsFzmynpv1zkvA5A7jA", "slug": "jisik_inside",       "name": "지식인사이드",       "tab": "videos"},
    {"id": "UC6kZpTl39-_SqfBrF1-N2oQ", "slug": "yonhap_economy",     "name": "연합뉴스경제TV",     "tab": "videos"},
    {"id": "UCvrOll07bwpNzGhBHRB5_yw", "slug": "developmong",        "name": "웅덩이매수디벨롭몽", "tab": "videos"},
    {"id": "",                           "slug": "doniggangpae",       "name": "돈이깡패다",          "tab": "videos", "handle": "돈이깡패다"},
    {"id": "UCIipmgxpUxDmPP-ma3Ahvbw", "slug": "mk_wallstreet",      "name": "매경 월가월부",      "tab": "videos"},
    {"id": "UChY8VUjXv0aA7RF9hDQ0ISg", "slug": "sbs_gyoyangi",       "name": "교양이를 부탁해",    "tab": "videos"},
    {"id": "",                           "slug": "aspim_research",     "name": "애스핌 리서치",      "tab": "videos", "handle": "ASPIM_research"},
    # 머니코믹스에서 분리된 두 채널 (2026-08 확인)
    # 알상무: 머니코믹스 하차 후 독립. 매일 아침 "당일전략"(9~19분)이 핵심이라 쇼츠 필터를 걸지 않는다.
    {"id": "UCiDmfbYvuMEVbRxPmFP4sng", "slug": "alsangmoo",          "name": "알상무",             "tab": "videos", "handle": "rsangmoo"},
    # 위폴: 머니코믹스 아침방송 [바이킹스]가 분리된 슈카친구들 채널. 평일 아침 7시 20분 라이브.
    {"id": "UCMnFS27HnroIc1D4ct37TUA", "slug": "wepoll",             "name": "위폴",               "tab": "videos", "handle": "wepoll_original"},
    # 먹방 신규 (2026-10-19). 세 채널 모두 유튜브 자동 자막이 있다. 백종원은 제외(사용자 지시).
    {"id": "UCA6KBBX8cLwYZNepxlE_7SA", "slug": "heebab",             "name": "히밥",               "tab": "videos"},
    # 성시경 본채널. 노래·라디오 영상이 섞여 있어 제목에 "먹을텐데"가 있는 회차만 받는다.
    {"id": "UCl23-Cci_SMqyGXE1T_LYUg", "slug": "sungsikyung",        "name": "먹을텐데",           "tab": "videos",
     "title_include": "먹을텐데"},
    {"id": "UCqVjsRNWQM-ZBl27Pp8qI5g", "slug": "chureupkyeon",       "name": "츄릅켠",             "tab": "videos", "handle": "chureupkyeon"},
]


def food_channels() -> list[dict]:
    """맛집 파이프라인 대상 채널."""
    return [c for c in CHANNELS if c["slug"] in FOOD_SLUGS]


# === 카테고리 정책 ===
# 미래 정책(workers, max_videos 등)도 같은 dict에 추가 가능
# min_duration_sec > 0 이면 크롤 시 그 길이 미만 영상(쇼츠/단편) 제외
# summary_days: 요약 큐에 넣을 영상의 나이 상한. 0 = 제한 없음(전부).
#   시황·뉴스처럼 시의성이 전부인 콘텐츠는 한 달이 지나면 읽히지 않으므로 30일로 끊는다.
#   교양(culture)은 개별 영상의 수명이 길어 오래된 것도 값이 있어 제한을 두지 않는다.
#   days(크롤 범위)와는 별개 축이다 — 수집은 하되 요약만 안 할 수 있다.
# crawl_cap: 크롤 1회차에 시도할 영상 수 상한. 없거나 0 = 무제한.
#   heavy는 큐가 수백 건(삼프로TV days=60 → 809건)이라 스로틀 상태에서 회차를 끝없이 늘린다.
CATEGORY_POLICY = {
    "stock_econ":   {"days": 30, "summary": True,  "min_duration_sec": 0,   "summary_days": 30},
    "news":         {"days": 30, "summary": True,  "min_duration_sec": 180, "summary_days": 30},
    "invest_media": {"days": 30, "summary": True,  "min_duration_sec": 180, "summary_days": 30},
    "culture":      {"days": 30, "summary": True,  "min_duration_sec": 180, "summary_days": 0},
    "food":         {"days": 60, "summary": False, "min_duration_sec": 0,   "summary_days": 0},
    "heavy":        {"days": 60, "summary": False, "min_duration_sec": 0,   "summary_days": 0, "crawl_cap": 30},  # sampro_tv 등
}

DEFAULT_POLICY = {"days": 30, "summary": False, "min_duration_sec": 0, "summary_days": 0}


def summary_window_sql(alias: str = "") -> str:
    """요약 큐용 published_at 조건 SQL. 카테고리별 summary_days를 그대로 반영한다.

    경제(시황·뉴스·투자미디어)는 30일, 교양은 제한 없음 — 한 쿼리에서 채널마다
    다른 창을 적용해야 해서 OR로 펼친다. 반환값은 괄호로 감싼 단일 조건식.
    """
    col = f"{alias}." if alias else ""
    limited: dict[int, list[str]] = {}
    unlimited: list[str] = []
    for slug in SUMMARY_SLUGS:
        d = policy_for(slug).get("summary_days", 0)
        if d and d > 0:
            limited.setdefault(d, []).append(slug)
        else:
            unlimited.append(slug)

    parts = []
    for days, slugs in sorted(limited.items()):
        names = ",".join(f"'{s}'" for s in slugs)
        parts.append(
            f"({col}channel_slug IN ({names})"
            f" AND {col}published_at >= NOW() - INTERVAL '{days} days')"
        )
    if unlimited:
        names = ",".join(f"'{s}'" for s in unlimited)
        parts.append(f"({col}channel_slug IN ({names}))")
    return "(" + " OR ".join(parts) + ")"


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

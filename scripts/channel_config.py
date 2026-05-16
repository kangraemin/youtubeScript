"""채널 분류 — 요약 대상 / 제외 대상.

다른 스크립트들이 import해서 사용한다:
    from scripts.channel_config import STOCK_ECON_SLUGS
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

# 요약 제외 집합 (food + 영상 수 너무 많은 sampro_tv는 별도 정책)
EXCLUDED_FROM_SUMMARY = set(FOOD_SLUGS) | {"sampro_tv"}

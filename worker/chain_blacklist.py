"""공용 체인점 이름 블랙리스트.

AI 프롬프트(restaurant_extractor)와 description 파서 양쪽이 참조한다.
부분 매칭이라 '맘스터치 서울시청점' 같은 지점명도 차단된다.
"""

CHAIN_NAMES = [
    "롯데리아", "맥도날드", "버거킹", "KFC", "맘스터치",
    "스타벅스", "이디야", "커피빈", "투썸플레이스",
    "파리바게뜨", "뚜레쥬르", "배스킨라빈스", "서브웨이",
    "도미노피자", "피자헛", "미스터피자",
    "BBQ", "BHC", "교촌", "네네치킨", "굽네치킨",
    "GS25", "CU", "세븐일레븐", "이마트24",
    "본죽", "놀부", "한솥도시락",
]


def is_chain(name: str | None) -> bool:
    """가게 이름이 체인점 블랙리스트에 포함되면 True (부분 매칭)."""
    if not name:
        return False
    return any(ch in name for ch in CHAIN_NAMES)

"""같은 가게인지 볼 때 쓰는 주소 열쇠.

네이버 검색은 '서울 강남구 …', 지오코딩·옛 수집은 '서울특별시 강남구 …'처럼 시·도 표기가 달라
(name, address) 정확 일치로는 같은 가게를 못 찾고 새로 넣었다(먹맵 중복 185묶음, 2026-11-10).
맨 앞 시·도 토큰을 떼고 공백을 없앤 나머지를 열쇠로 쓴다. 시·도가 달라도 나머지가 같은 경우를 막으려고
비교할 때는 좌표가 가까운지도 같이 본다(same_place).
"""
import math
import re

# 시·도 표기(긴 이름·짧은 이름·통합 이후 이름). 맨 앞 토큰이 이 중 하나면 뗀다
_PROVINCES = {
    "서울", "서울시", "서울특별시", "부산", "부산광역시", "대구", "대구광역시", "인천", "인천광역시",
    "광주", "광주광역시", "대전", "대전광역시", "울산", "울산광역시", "세종", "세종시", "세종특별자치시",
    "경기", "경기도", "강원", "강원도", "강원특별자치도", "충북", "충청북도", "충남", "충청남도",
    "전북", "전라북도", "전북특별자치도", "전남", "전라남도", "경북", "경상북도", "경남", "경상남도",
    "제주", "제주도", "제주특별자치도", "전남광주", "전남광주통합특별시",
}


def address_key(address: str | None) -> str | None:
    if not address:
        return None
    parts = address.split()
    if parts and parts[0] in _PROVINCES:
        parts = parts[1:]
    key = re.sub(r"\s+", "", "".join(parts))
    return key or None


def _km(a: dict, b: dict) -> float:
    la1, lo1, la2, lo2 = map(math.radians, (a["lat"], a["lng"], b["lat"], b["lng"]))
    h = math.sin((la2 - la1) / 2) ** 2 + math.cos(la1) * math.cos(la2) * math.sin((lo2 - lo1) / 2) ** 2
    return 6371 * 2 * math.asin(math.sqrt(h))


def same_place(a: dict, b: dict, max_km: float = 0.3) -> bool:
    """이름이 같고 시·도를 뗀 주소가 같으며, 두 쪽 다 좌표가 있으면 300m 안이다."""
    if (a.get("name") or "").replace(" ", "") != (b.get("name") or "").replace(" ", ""):
        return False
    ka, kb = address_key(a.get("address")), address_key(b.get("address"))
    if not ka or ka != kb:
        return False
    if a.get("lat") is not None and a.get("lng") is not None and b.get("lat") is not None and b.get("lng") is not None:
        return _km(a, b) <= max_km
    return True

import logging
import os
import re
import requests

logger = logging.getLogger(__name__)

REGION_MAP = {
    "서울": "서울",
    "경기": "경기",
    "인천": "인천",
    "부산": "부산",
    "대구": "대구",
    "대전": "대전",
    "광주": "광주",
    "울산": "울산",
    "세종": "세종",
    "강원": "강원",
    # 도(道) 풀네임은 짧은 키가 substring으로 매칭되지 않아 별도로 추가
    "충청북도": "충북",
    "충북": "충북",
    "충청남도": "충남",
    "충남": "충남",
    "전라북도": "전북",
    "전북": "전북",
    "전라남도": "전남",
    "전남": "전남",
    "경상북도": "경북",
    "경북": "경북",
    "경상남도": "경남",
    "경남": "경남",
    "제주": "제주",
}

# 주소-힌트 매칭용 지역 키워드. 광역 + 구/군/시 단위.
REGION_KEYWORDS = [
    "서울", "경기", "인천", "부산", "대구", "대전",
    "광주", "울산", "세종", "강원",
    "충북", "충남", "전북", "전남", "경북", "경남", "제주",
    # 서울 구
    "강남구", "서초구", "송파구", "마포구", "용산구", "성동구", "광진구",
    "종로구", "강서구", "양천구", "영등포구", "구로구", "금천구",
    "동작구", "관악구", "성북구", "도봉구", "노원구", "강북구", "은평구",
    "서대문구", "동대문구", "중랑구", "강동구",
    # 경기/인천 주요
    "수원", "성남", "고양", "용인", "부천", "안산", "안양",
    "의정부", "시흥", "파주", "광명", "하남", "남양주", "화성", "평택",
    # 부산
    "기장", "해운대", "수영", "사하", "사상", "동래", "금정", "영도", "연제",
    # 충청
    "청원", "흥덕", "청주", "유성", "대덕", "완산", "덕진",
    "아산", "천안", "공주", "논산",
    # 호남
    "광양", "여수", "순천", "목포", "군산", "전주",
    # 제주
    "제주시", "서귀포", "우도", "애월", "조천", "함덕",
]

API_URL = "https://openapi.naver.com/v1/search/local.json"


def _strip_html(text: str) -> str:
    return re.sub(r"<[^>]+>", "", text)


def _extract_region(address: str) -> str | None:
    for keyword, region in REGION_MAP.items():
        if keyword in address:
            return region
    return None


def _hint_regions(hint: str | None) -> list[str]:
    """address_hint 문자열에서 REGION_KEYWORDS와 매칭되는 단어들을 뽑는다."""
    if not hint:
        return []
    return [kw for kw in REGION_KEYWORDS if kw in hint]


def _search_candidates(query: str) -> list[dict]:
    """네이버 Local Search에서 후보 5개를 받는다."""
    headers = {
        "X-Naver-Client-Id": os.environ["NAVER_SEARCH_CLIENT_ID"],
        "X-Naver-Client-Secret": os.environ["NAVER_SEARCH_CLIENT_SECRET"],
    }
    try:
        resp = requests.get(
            API_URL, headers=headers,
            params={"query": query, "display": 5}, timeout=10,
        )
        resp.raise_for_status()
        return resp.json().get("items", [])
    except Exception as e:
        logger.warning("Naver search failed for '%s': %s", query, e)
        return []


def _admin_stems(address: str) -> list[str]:
    """주소의 시·군·구·읍·면 이름에서 끝 글자를 뗀 줄기(2자 이상). "충청북도 단양군 가곡면" → ["단양", "가곡"]."""
    stems = []
    for w in address.split():
        m = re.fullmatch(r"([가-힣]{2,})(시|군|구|읍|면)", w)
        if m and "특별" not in m.group(1) and "광역" not in m.group(1):
            stems.append(m.group(1))
    return stems


def _region_score(addr: str, regions: list[str], hint: str) -> int:
    """hint 지역 키워드 수 + 주소의 시·군·구 이름이 hint에 나온 수."""
    score = sum(1 for kw in regions if kw in addr)
    if hint:
        score += sum(1 for st in _admin_stems(addr) if st in hint and st not in regions)
    return score


def _pick_best(items: list[dict], regions: list[str], hint: str = "") -> tuple[dict | None, int]:
    """후보 중 hint 지역이 주소에 많이 들어간 것을 고른다. (후보, 지역 점수)를 돌려준다.

    hint에 지역 단서가 없으면 첫 결과(점수 0).
    지역 단서가 있는데 모든 후보가 불일치면 (None, 0) (false positive 방지).
    REGION_KEYWORDS에 없는 시·군(고흥·단양 등)은 주소의 행정구역 이름이 hint에 있는지로 맞춘다.
    """
    if not items:
        return None, 0
    scored = []
    for it in items:
        addr = it.get("roadAddress") or it.get("address", "")
        scored.append((_region_score(addr, regions, hint or ""), it))
    scored.sort(key=lambda x: -x[0])
    top_score, top_item = scored[0]
    if top_score > 0:
        return top_item, top_score
    return (items[0], 0) if not regions else (None, 0)


def _norm_name(s: str) -> str:
    words = _strip_html(s or "").split()
    # 띄어 쓴 마지막 단어가 "○○점"이면 지점명으로 보고 뗀다(붙여 쓴 이름은 건드리지 않는다)
    if len(words) > 1 and words[-1].endswith("점"):
        words = words[:-1]
    return re.sub(r"[^가-힣A-Za-z0-9]", "", "".join(words)).lower()


def name_similar(a: str, b: str) -> bool:
    """공백·지점명("○○점")·문장부호를 지운 뒤 한쪽이 다른 쪽을 포함하면 같은 가게로 본다."""
    x, y = _norm_name(a), _norm_name(b)
    if not x or not y:
        return False
    return x in y or y in x


def search_restaurant(name: str, address_hint: str = "") -> dict | None:
    """Search for a restaurant using 3-stage query fallback + region filter.

    1) `{hint} {name}` → 2) `{name}` → 3) `{name} 맛집` 순으로 시도.
    각 결과에서 hint의 지역 키워드가 주소에 포함된 것만 채택.
    한 단계에서 지역 일치 후보가 없으면 다음 쿼리로 이동.

    Returns dict(name, confidence, address, lat, lng, region, naver_place_id) or None.
    """
    regions = _hint_regions(address_hint)
    queries = []
    if address_hint:
        queries.append(f"{address_hint} {name}")
    queries.append(name)
    queries.append(f"{name} 맛집")

    for query in queries:
        items = _search_candidates(query)
        item, region_score = _pick_best(items, regions, address_hint)
        if not item:
            continue
        try:
            lat = int(item["mapy"]) / 10_000_000
            lng = int(item["mapx"]) / 10_000_000
        except (ValueError, KeyError):
            lat, lng = None, None
        road_address = item.get("roadAddress", "")
        address = road_address or item.get("address", "")
        region = _extract_region(address)
        found_name = _strip_html(item.get("title", name))
        # 지역 힌트가 주소와 맞고 이름도 비슷해야 high. 나머지는 관리자 검수(is_visible=false)로 보낸다
        confidence = "high" if region_score >= 1 and name_similar(name, found_name) else "low"
        return {
            "name": found_name,
            "confidence": confidence,
            "address": address,
            "lat": lat,
            "lng": lng,
            "region": region,
            "naver_place_id": None,
        }

    return None

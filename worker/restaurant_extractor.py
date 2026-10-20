"""먹방 영상 자막에서 실제 방문한 식당을 뽑는다 — claude -p(구독 CLI, API 키 아님).

결정 _global/process/no-anthropic-api-calls: 코드에서 Anthropic API를 부르지 않는다.
실패(CLI 오류·JSON 깨짐)는 ExtractError로 올려서 "가게 없음"과 구분한다.
"""
import json
import logging
import os
import re
import subprocess

from chain_blacklist import CHAIN_NAMES

logger = logging.getLogger(__name__)

# 프롬프트나 스키마를 바꾸면 올린다. processing_queue.prompt_version이 다르면 다시 처리 대상이 된다.
PROMPT_VERSION = "v4-2026-10-20"
CLAUDE = os.path.expanduser("~/.local/bin/claude")
MODEL = os.environ.get("EXTRACT_MODEL", "sonnet")
# 기본 지시문·도구·설정을 빼면 호출당 고정 비용이 4만 5천 → 600토큰으로 준다(--bare는 API 키 인증이라 안 씀)
FLAGS = ["--output-format", "json", "--system-prompt", "먹방 자막에서 방문 식당을 뽑아 JSON 하나만 출력하는 추출기다.",
         "--tools", "", "--strict-mcp-config", "--setting-sources", "", "--no-session-persistence"]
MAX_TRANSCRIPT_CHARS = 40_000
# 요약은 claude -p로만 한다. 막히면 그 회차를 멈춘다(Codex로 넘기지 않는다, 사용자 지시 2026-10-20)


# .env.local에 ANTHROPIC_API_KEY가 있으면 claude -p가 구독 대신 API 키로 과금한다(실측: "Credit balance is too low").
# 자식 프로세스 env에서 빼서 항상 구독 계정 로그인으로 돌게 한다.
_API_ENV = ("ANTHROPIC_API_KEY", "ANTHROPIC_AUTH_TOKEN", "ANTHROPIC_BASE_URL")


def _cli_env() -> dict:
    return {k: v for k, v in os.environ.items() if k not in _API_ENV}


class ExtractError(Exception):
    """추출 자체가 실패했다(가게 0개와 다름). 재시도 대상."""


class ExtractBlocked(ExtractError):
    """로그인 만료·사용 한도처럼 영상과 무관하게 전부 실패하는 경우. 회차를 멈추고 재시도 횟수는 쓰지 않는다."""


_BLOCKED = re.compile(r"authenticat|OAuth|log ?in|hit your .*limit|usage limit|rate limit", re.I)


_CHAIN_LINE = ", ".join(CHAIN_NAMES)

# __CHAINS__ 토큰 치환 방식으로 f-string {} JSON 중괄호 충돌을 회피한다.
_PROMPT_BODY = """다음은 유튜브 영상의 제목, 설명, 자막입니다.
이 영상에서 유튜버가 **실제로 방문하여 음식을 먹은** 음식점만 추출해주세요.

영상 제목: {title}

영상 설명:
{description}

자막 (타임스탬프 포함):
{transcript}

다음 JSON 형식으로만 응답하세요 (다른 텍스트 없이):
{{"restaurants": [{{"name": "가게명", "address_hint": "구체적 지역", "category": "카테고리", "rating": "평가", "summary": "한줄평", "is_ad": false, "timestamp_seconds": 0, "visited": true, "menu": "먹은 메뉴와 양", "price": "영상에서 말한 가격", "quote": "유튜버 발언 원문", "why": "추천 이유 또는 아쉬운 점", "detail": {{"recommend": "강추|추천|보통|아쉬움", "verdict": "총평", "dishes": [{{"name": "메뉴", "comment": "맛 평가", "best": true, "ts": "MM:SS"}}], "pros": ["좋다고 한 점"], "cons": ["아쉽다고 한 점"], "price": "대표 가격", "wait": "웨이팅", "hours": "영업시간·휴무", "parking": "주차", "reserve": "예약", "solo_ok": "혼밥", "taste": "맛 특징", "portion": "양", "spicy_salty": "맵기·간", "vibe": "분위기", "service": "친절", "revisit": "재방문", "good_for": "어울리는 자리", "value": "가성비", "tips": ["방문 팁"]}}}}]}}

규칙:
- **실제 방문하여 먹는 장면이 있는 경우만** 추출. 단순 언급/경품/이벤트/회의는 제외
- **프랜차이즈 체인점 제외**: __CHAINS__ 등 전국 체인점은 제외 (소규모 로컬 체인 2~3개 매장은 포함 가능)
- 영상 설명에 가게 정보(이름, 주소)가 있으면 **설명을 우선 참조**
- 설명에 "광고", "협찬", "유료광고"가 있으면 is_ad=true
- 가게명 맞춤법 교정 (발음대로 적힌 이름을 올바른 이름으로, 예: 성계향→성게향)
- **address_hint 규칙 (동명이인 방지 최우선)**:
  1. 자막/설명에 **구/동/길 이름**이 나오면 반드시 포함 (예: "서울 광진구 자양동 아차산로 305", "청주 청원구 향군로")
  2. 구/동 모르면 **시장/지하철역/랜드마크** 포함 (예: "기장시장", "청량리역 근처")
  3. 그것도 없고 **시/광역시만** 나오면 광역명만 (예: "서울", "제주")
  4. 지역 정보 전혀 없으면 빈 문자열
  → 광역만 있는 hint는 검색 실패율 높음. 자막/설명 꼼꼼히 읽고 구/동/랜드마크 찾을 것
- category: 한식/일식/중식/양식/카페/디저트/분식/고기/구이/해산물/기타 중 택1
- rating: 강력추천/추천/보통/비추/언급없음 중 택1 (유튜버의 반응 기반)
- summary: 유튜버가 언급한 핵심 한줄평 (30자 이내)
- timestamp_seconds: 해당 가게가 처음 언급되는 시점(초), 정수. 자막의 [H:MM:SS] 또는 [MM:SS]를 초로 바꾼다
- visited: 유튜버가 그 가게에 **직접 가서** 먹었으면 true. 배달·포장·택배로 받아 먹었거나 이름만 언급했으면 false
- menu: 실제로 먹은 메뉴와 양 (예: "육전 3인분, 물냉면"). 모르면 ""
- price: 영상에서 말한 가격만 (예: "육전 1인분 15,000원"). 말하지 않았으면 "" — 추측 금지
- quote: 그 가게 음식에 대한 유튜버의 말을 **자막에 적힌 그대로** 1~2문장(80자 이내) 복사. 고치거나 지어내지 말 것. 적당한 말이 없으면 ""
- why: 추천 이유 또는 아쉬운 점 한 문장 (30자 이내)
- detail: 그 가게에 대해 **유튜버가 실제로 한 말만** 근거로 채운다. 말하지 않은 항목은 "" 또는 [] — 추측·일반론 금지
  - recommend: 강추=극찬·재방문/강력 추천 발언, 추천=맛있다는 반응 위주, 보통=무난·호불호, 아쉬움=단점 위주
  - verdict: 지도 카드·목록에 크게 보이는 한 줄 요약. **30자 안팎(최대 40자), 해요체로 끝낸다**("~해요", "~예요")
    - 구조: [이 집의 대표 메뉴나 맛 특징] + [유튜버가 내린 핵심 평가]. 처음 보는 사람이 "왜 가야 하는지/말아야 하는지" 바로 알게
    - 메뉴 이름이나 구체적인 맛 특징을 반드시 하나 넣는다
    - 금지: 막연한 칭찬("맛있는 집", "소중한 곳", "만족한 곳"), 과장 표현 그대로("미친", "극락"), 전달형("~라는 평", "극찬", "추천함"), 방문 과정 서술("처음 먹었는데", "1년 만에 다시"), 명사형 끝맺음("~집", "~곳", "~음")
    - 보통·아쉬움이면 좋은 점과 아쉬운 점을 짧게 함께
    - 좋은 예: "마늘 고추기름 탕수육이 바삭하고 독보적이에요" / "한우불고기가 육회처럼 부드럽고 간이 슴슴해요" / "짬뽕은 평범하고 볶음밥이 더 나아요"
    - 나쁜 예: "김치와 고기 모두 훌륭한, 어머님 정성이 담긴 소중한 집" / "진짜 미친 집이라며 찐맛집 5선 중 첫 번째로 꼽음"
  - dishes: 이 영상에서 **실제로 먹은** 메뉴만(말만 하고 안 먹은 것 제외), 최대 5개. comment는 맛 평가 30자 이내, 가장 맛있다고 한 메뉴 하나만 best=true, ts는 그 메뉴를 먹는 자막 시각
  - pros / cons: 각 최대 4개, 항목당 20자 이내. 메뉴 comment와 같은 말 반복 금지
  - price·wait·hours·parking·reserve·solo_ok: 화면 칩에 들어가므로 **20자 이내로 짧게**. price는 숫자와 "원"이 있는 대표 메뉴 가격 하나(예: "피자 L 29,000원"), 숫자 없으면 "". wait는 유튜버가 실제로 기다린 정도(예: "2시간 가까이", "20~25분", "바로 입장", "오픈 전 12팀")
  - taste: 맛 키워드 3개 이내(예: "짭짤, 불맛"). portion·spicy_salty·vibe·service·revisit·good_for·value: 각 40자 이내
  - tips: 주문 팁·먹는 법 등 최대 3개, 항목당 40자 이내
- 맛집 영상이 아닌 경우(노래, 브이로그, 회의, 이벤트 홍보 등) 빈 배열 반환
- 가게가 없으면 빈 배열: {{"restaurants": []}}
- JSON만 응답"""

EXTRACT_PROMPT = _PROMPT_BODY.replace("__CHAINS__", _CHAIN_LINE)


def _fmt(sec: float) -> str:
    sec = int(sec)
    h, rem = divmod(sec, 3600)
    m, s = divmod(rem, 60)
    return f"{h}:{m:02d}:{s:02d}" if h else f"{m:02d}:{s:02d}"


def _squash(s: str) -> str:
    return re.sub(r"[^가-힣A-Za-z0-9]", "", s or "")


def verify_quote(quote: str, transcript_text: str) -> str:
    """quote가 자막에 실제로 있는 문장일 때만 남긴다(공백·문장부호 무시). 없으면 "" — 지어낸 인용 방지."""
    q = _squash(quote)
    if len(q) < 4:
        return ""
    return quote.strip() if q in _squash(transcript_text) else ""


DETAIL_TEXT = {"recommend": 6, "verdict": 40, "price": 20, "wait": 20, "hours": 20, "parking": 20, "reserve": 20,
               "solo_ok": 20, "taste": 30, "portion": 40, "spicy_salty": 40, "vibe": 40, "service": 40,
               "revisit": 40, "good_for": 40, "value": 40}
DETAIL_LIST = {"pros": (4, 20), "cons": (4, 20), "tips": (3, 40)}
RECOMMEND = {"강추", "추천", "보통", "아쉬움"}
_NONE = re.compile(r"^(없음|언급\s*없음|미언급|해당\s*없음|정보\s*없음|-|n/?a)$", re.I)


def _txt(v, n: int) -> str:
    s = re.sub(r"\s+", " ", str(v or "")).strip()
    if not s or _NONE.match(s):
        return ""
    return s if len(s) <= n else s[: n - 1] + "…"


def clean_detail(d) -> dict | None:
    """상세 요약을 화면 규칙(빈말 제거·길이·개수 상한)에 맞게 다듬는다. 남는 게 없으면 None."""
    if not isinstance(d, dict):
        return None
    out: dict = {k: _txt(d.get(k), n) for k, n in DETAIL_TEXT.items()}
    if out["recommend"] not in RECOMMEND:
        out["recommend"] = ""
    if out["price"] and not re.search(r"\d", out["price"]):
        out["price"] = ""
    for k, (cnt, n) in DETAIL_LIST.items():
        xs = d.get(k) if isinstance(d.get(k), list) else []
        out[k] = [t for t in (_txt(x, n) for x in xs) if t][:cnt]
    dishes = []
    for x in d.get("dishes") if isinstance(d.get("dishes"), list) else []:
        if isinstance(x, dict) and _txt(x.get("name"), 30):
            dishes.append({"name": _txt(x.get("name"), 30), "comment": _txt(x.get("comment"), 30),
                           "best": bool(x.get("best")), "ts": _txt(x.get("ts"), 8)})
    out["dishes"] = sorted(dishes, key=lambda x: not x["best"])[:5]
    out = {k: v for k, v in out.items() if v}
    return out or None


def _run_claude(prompt: str) -> tuple[str, dict]:
    r = None
    try:
        r = subprocess.run([CLAUDE, "-p", prompt, "--model", MODEL, *FLAGS],
                           capture_output=True, text=True, timeout=300, cwd="/tmp", env=_cli_env())
        res = json.loads(r.stdout)
    except subprocess.TimeoutExpired as e:
        raise ExtractError("claude -p 시간 초과") from e
    except (json.JSONDecodeError, OSError) as e:
        raise ExtractError(f"claude -p 출력 이상: {(r.stderr if r else str(e))[:200]}") from e
    if res.get("is_error"):
        msg = str(res.get("result", ""))[:200]
        raise (ExtractBlocked if _BLOCKED.search(msg) else ExtractError)(msg)
    u = res.get("usage", {}) or {}
    usage = {
        "input_tokens": int(u.get("input_tokens", 0)) + int(u.get("cache_read_input_tokens", 0))
        + int(u.get("cache_creation_input_tokens", 0)),
        "output_tokens": int(u.get("output_tokens", 0)),
    }
    return res.get("result", ""), usage


def extract_restaurants(
    transcript_segments: list[dict],
    title: str = "",
    description: str = "",
) -> tuple[list[dict], dict]:
    """자막에서 직접 방문한 식당 목록을 뽑는다.

    Returns (restaurants, usage). visited=false는 빼고, quote는 자막 대조를 통과한 것만 남긴다.
    Raises ExtractError: CLI 실패·시간 초과·JSON 파싱 실패.
    """
    transcript_text = "\n".join(f"[{_fmt(seg['start'])}] {seg['text']}" for seg in transcript_segments)
    if len(transcript_text) > MAX_TRANSCRIPT_CHARS:
        transcript_text = transcript_text[:MAX_TRANSCRIPT_CHARS] + "\n... (자막 생략)"
    desc_text = description[:2000] if description else "(설명 없음)"
    prompt = EXTRACT_PROMPT.format(
        title=title or "(제목 없음)", description=desc_text, transcript=transcript_text,
    )

    text, usage = _run_claude(prompt)

    m = re.search(r"\{.*\}", text, re.S)
    if not m:
        raise ExtractError(f"JSON 없음: {text[:200]}")
    try:
        data = json.loads(re.sub(r",\s*([}\]])", r"\1", m.group(0)))  # 끝 쉼표 허용
    except json.JSONDecodeError as e:
        raise ExtractError(f"JSON 파싱 실패: {e}") from e

    plain_text = " ".join(seg["text"] for seg in transcript_segments)
    out = []
    for rest in data.get("restaurants", []) or []:
        if not isinstance(rest, dict) or not rest.get("name"):
            continue
        if rest.get("visited") is False:
            logger.info("직접 방문 아님 → 제외: %s", rest.get("name"))
            continue
        # 줄 사이 타임스탬프 숫자가 끼면 여러 줄에 걸친 인용이 대조에 실패하므로 본문만 이어 붙여 비교한다
        rest["quote"] = verify_quote(rest.get("quote", ""), plain_text)
        for k in ("menu", "price", "why"):
            rest[k] = (rest.get(k) or "").strip()
        rest["detail"] = clean_detail(rest.get("detail"))
        out.append(rest)
    return out, usage

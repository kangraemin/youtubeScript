"""먹방 영상 자막에서 실제 방문한 식당을 뽑는다 — claude -p(구독 CLI, API 키 아님).

결정 _global/process/no-anthropic-api-calls: 코드에서 Anthropic API를 부르지 않는다.
실패(CLI 오류·JSON 깨짐)는 ExtractError로 올려서 "가게 없음"과 구분한다.
"""
import json
import logging
import os
import re
import shutil
import subprocess
import tempfile

from chain_blacklist import CHAIN_NAMES

logger = logging.getLogger(__name__)

# 프롬프트나 스키마를 바꾸면 올린다. processing_queue.prompt_version이 다르면 다시 처리 대상이 된다.
PROMPT_VERSION = "v2-2026-10-19"
CLAUDE = os.path.expanduser("~/.local/bin/claude")
MODEL = os.environ.get("EXTRACT_MODEL", "sonnet")
# 기본 지시문·도구·설정을 빼면 호출당 고정 비용이 4만 5천 → 600토큰으로 준다(--bare는 API 키 인증이라 안 씀)
FLAGS = ["--output-format", "json", "--system-prompt", "먹방 자막에서 방문 식당을 뽑아 JSON 하나만 출력하는 추출기다.",
         "--tools", "", "--strict-mcp-config", "--setting-sources", "", "--no-session-persistence"]
MAX_TRANSCRIPT_CHARS = 40_000
# claude -p가 로그인 만료·한도로 막히면 codex exec로 넘어간다. EXTRACT_FALLBACK=off면 끈다.
CODEX = None if os.environ.get("EXTRACT_FALLBACK") == "off" else shutil.which("codex") or (
    "/opt/homebrew/bin/codex" if os.path.exists("/opt/homebrew/bin/codex") else None)
CODEX_MODEL = os.environ.get("EXTRACT_CODEX_MODEL", "")
_claude_blocked = False


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
{{"restaurants": [{{"name": "가게명", "address_hint": "구체적 지역", "category": "카테고리", "rating": "평가", "summary": "한줄평", "is_ad": false, "timestamp_seconds": 0, "visited": true, "menu": "먹은 메뉴와 양", "price": "영상에서 말한 가격", "quote": "유튜버 발언 원문", "why": "추천 이유 또는 아쉬운 점"}}]}}

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


def _run_codex(prompt: str) -> tuple[str, dict]:
    """claude -p가 막혔을 때 쓰는 예비 추출기(Codex 구독 CLI). 토큰 수는 CLI가 주지 않아 0으로 둔다."""
    with tempfile.NamedTemporaryFile("r", suffix=".txt") as out:
        try:
            r = subprocess.run([CODEX, "exec", "--skip-git-repo-check", "--ephemeral", "-s", "read-only",
                                *(["-m", CODEX_MODEL] if CODEX_MODEL else []), "-o", out.name, "-"],
                               input=prompt, capture_output=True, text=True, timeout=600, cwd="/tmp",
                               env=_cli_env())
        except subprocess.TimeoutExpired as e:
            raise ExtractError("codex exec 시간 초과") from e
        except OSError as e:
            raise ExtractError(f"codex exec 실행 실패: {e}") from e
        text = out.read()
    if r.returncode != 0 or not text.strip():
        msg = (r.stderr or r.stdout)[-200:]
        raise (ExtractBlocked if _BLOCKED.search(msg) else ExtractError)(f"codex exec: {msg}")
    return text, {"input_tokens": 0, "output_tokens": 0}


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

    global _claude_blocked
    if _claude_blocked and CODEX:
        text, usage = _run_codex(prompt)
    else:
        try:
            text, usage = _run_claude(prompt)
        except ExtractBlocked as e:
            # 로그인 만료·한도면 이 프로세스에선 codex로만 돈다(영상마다 claude를 다시 두드리지 않는다)
            if not CODEX:
                raise
            logger.warning("claude -p 막힘 → codex exec로 전환: %s", e)
            _claude_blocked = True
            text, usage = _run_codex(prompt)

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
        out.append(rest)
    return out, usage

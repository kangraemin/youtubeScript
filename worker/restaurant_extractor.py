import json
import logging
import os
from anthropic import Anthropic

from chain_blacklist import CHAIN_NAMES

logger = logging.getLogger(__name__)

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
{{"restaurants": [{{"name": "가게명", "address_hint": "구체적 지역", "category": "카테고리", "rating": "평가", "summary": "한줄평", "is_ad": false, "timestamp_seconds": 0}}]}}

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
- timestamp_seconds: 해당 가게가 처음 언급되는 시점(초), 정수
- 맛집 영상이 아닌 경우(노래, 브이로그, 회의, 이벤트 홍보 등) 빈 배열 반환
- 가게가 없으면 빈 배열: {{"restaurants": []}}
- JSON만 응답"""

EXTRACT_PROMPT = _PROMPT_BODY.replace("__CHAINS__", _CHAIN_LINE)


def extract_restaurants(
    transcript_segments: list[dict],
    title: str = "",
    description: str = "",
) -> tuple[list[dict], dict]:
    """Extract restaurant info from transcript using Claude Haiku.

    Returns (restaurants_list, token_usage_dict).
    token_usage_dict: {"input_tokens": int, "output_tokens": int}
    """
    lines = []
    for seg in transcript_segments:
        minutes = int(seg["start"] // 60)
        seconds = int(seg["start"] % 60)
        lines.append(f"[{minutes:02d}:{seconds:02d}] {seg['text']}")
    transcript_text = "\n".join(lines)

    if len(transcript_text) > 15000:
        transcript_text = transcript_text[:15000] + "\n... (자막 생략)"

    desc_text = description[:2000] if description else "(설명 없음)"

    client = Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

    text = ""
    try:
        response = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=2000,
            messages=[
                {
                    "role": "user",
                    "content": EXTRACT_PROMPT.format(
                        title=title or "(제목 없음)",
                        description=desc_text,
                        transcript=transcript_text,
                    ),
                }
            ],
        )

        token_usage = {
            "input_tokens": response.usage.input_tokens,
            "output_tokens": response.usage.output_tokens,
        }

        text = response.content[0].text.strip()

        if text.startswith("```"):
            text = text.split("```")[1]
            if text.startswith("json"):
                text = text[4:]
            text = text.strip()

        data = json.loads(text)
        restaurants = data.get("restaurants", [])
        return restaurants, token_usage

    except json.JSONDecodeError as e:
        logger.error("JSON parse failed: %s / response: %s", e, text[:200])
        return [], {"input_tokens": 0, "output_tokens": 0}
    except Exception as e:
        logger.error("Claude API error: %s", e)
        return [], {"input_tokens": 0, "output_tokens": 0}

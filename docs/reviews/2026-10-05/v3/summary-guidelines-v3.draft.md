# 요약 가이드라인 v3 (초안 — prompts/summary-guidelines.md 교체 후보)

**철학 전환**: v2는 "영상을 안 봐도 화자가 한 말을 다 알 수 있게"(무손실 추출)였다. v3는 **"2분 안에 이 영상의 결론과 근거를 알고, 볼지 말지 정할 수 있게"**(독자 우선)로 바꾼다. 무손실이 필요한 독자는 원문 transcript와 chapters의 타임스탬프 링크로 간다. 요약이 원문을 대체하려고 원문보다 길어지면 안 된다.

## 출력 스키마

```json
{
  "schema": "v3",
  "content_type": "market_brief | interview | deep_analysis | explainer | news_digest | entertainment | clip",
  "tldr": "한 문장 결론. 누가 + 무엇을 주장/결정 + 핵심 근거 1개. 120자 이내",
  "watch_guide": {"verdict": "skip | skim | watch", "why": "1~2문장. 요약으로 충분한지, 원본에서 볼 구간(ts)"},
  "key_points": [
    {"id": "k1", "point": "주장 한 줄(40자 이내)", "detail": "근거·수치·맥락 1~3문장", "ts": "H:MM:SS", "quote": "근거 발화 원문 1개(150자 이내, 선택)"}
  ],
  "positions": [
    {"asset": "종목/자산", "action": "buy|sell|add|reduce|hold|plan_buy|plan_sell", "when": "done|today|conditional",
     "condition": "조건부일 때만", "detail": "평단·비중 등", "speaker": "이름|null", "ts": "", "quote": "필수"}
  ],
  "scenarios": [ {"if": "조건", "then": "화자가 말한 결과/대응", "ts": ""} ],
  "numbers":   [ {"fact": "검증·재인용 가능한 수치 1개", "ts": ""} ],
  "terms":     [ {"term": "", "explain": "1~2문장", "source": "영상|보충"} ],
  "takeaways": [ {"type": "rule|counter|reference", "text": "", "ts": ""} ],
  "chapters":  [ {"ts": "", "title": "20자 내외"} ],
  "entities":  ["정규화된 종목·지수·인물명 — 검색/필터용"],
  "open_questions": ["화자가 판단 유보했거나 확인이 필요한 것"]
}
```

## 핵심 규칙 (v2 대비 변경점)

1. **한 사실은 한 곳에만.** key_points에 쓴 수치는 numbers에 다시 쓰지 않는다. scenarios의 내용을 positions·takeaways에 다시 쓰지 않는다. 반복하고 싶으면 `(k2)`처럼 id로 참조한다.
2. **positions는 화자 본인의 실제 매매·계획만.** quote 안에 매매 동사(샀/팔/담/줄였/정리/손절/들어갔)나 계획 표현(사 볼까/팔고)이 있어야 한다. "좋아 보인다", "유튜버가 추천"은 key_points로. 시청자 권유는 따로 섹션을 만들지 않고 key_points 또는 scenarios에 넣는다(v2 action_items 폐지 — 47%가 다른 섹션과 같은 quote 재사용).
3. **content_type이 섹션을 고른다.**
   - market_brief / deep_analysis / interview: 전 섹션 가능
   - explainer / news_digest: positions·scenarios는 화자가 명시했을 때만. 대부분 key_points + numbers + terms + takeaways
   - entertainment / clip(3분 미만): tldr + key_points 1~3개 + watch_guide만. 나머지는 생략(빈 배열 금지, 키 자체를 뺀다)
   - 경제와 무관한 회차는 억지로 경제 섹션을 채우지 말고 tldr에 그 사실을 적는다.
4. **분량 예산**: 출력 JSON 총 글자 수가 transcript 글자 수의 25%를 넘지 않게. key_points 3~7개(2시간+ 라이브는 최대 10개). numbers 최대 8, terms 최대 5(일반 용어 금지), takeaways 최대 5, chapters 5~15개.
5. **quote는 근거 1개만.** 항목당 quote 최대 1개, 150자 이내, transcript 원문 그대로(STT 오류 포함). 여러 줄을 "..."로 이어 붙이지 않는다. 같은 quote를 두 항목에 쓰지 않는다. numbers·terms·takeaways·chapters·scenarios는 quote 없이 ts만.
6. **모델 추론 금지 구역**: quote나 transcript에 없는 연도·이름·수치를 보태지 않는다. 화자가 말하지 않은 시청자 권고를 만들지 않는다. 보충 지식은 terms의 `source:"보충"`에서만 허용.
7. **후반부 커버리지**: chapters의 마지막 ts가 영상 길이의 85% 이후여야 한다. 아니면 전수 Read가 안 된 것이므로 다시 읽는다.

## 저장 전 자체 검증 (save_summary.py에서 기계 검증 권장)
- 모든 quote가 transcript에 부분 문자열로 존재하는가
- 출력 글자 수 ≤ transcript × 0.25 (clip은 ≤ 600자)
- 같은 quote 중복 0, numbers.fact가 key_points.detail에 그대로 있지 않은가
- chapters 마지막 ts ≥ 영상 길이 × 0.85

# 유튜브 주식·경제 transcript 요약 가이드라인 (v3)

이 파일은 요약 모델이 transcript 1편을 받아 아래 JSON 스키마로 출력하기 위한 톤·스키마 **단일 출처**다. 절차는 `.claude/commands/summarize-next.md`와 `.claude/workflows/summarize-batch.js`에 있고, 이 파일만 고쳐도 요약 결과가 바뀐다.
v2(13섹션 무손실 추출)에서 2026-10-09 교체. v2 정본과 비교 샘플은 `docs/reviews/2026-10-05/`에 있다. 웹은 `schema` 키가 없는 기존 v2 요약도 계속 렌더한다.

## 입력

`scripts/get_next_unsummarized.py`가 stdout JSON으로 메타데이터를 반환하고, transcript 본문은 `/tmp/summarize_target.txt`(병렬 sub-agent는 vid별 고유 경로)에 dump되어 있다. 필드:
- `vid`, `channel`, `channel_slug`, `title`, `published_at`, `url`
- `transcript_path` — `/tmp/summarize_target.txt`
- `transcript_chars`, `transcript_lines`
- `read_chunks`, `chunk_size` — Read 도구로 분할 읽기 위한 정보

**2026-10-13 사용자 교정**: 짧게 압축하느라 맥락·조건·설명·후반부를 빠뜨리면 안 된다. tldr는 빠른 개요일 뿐, 본문은 **소제목 → 요점 → 근거·수치·조건·반론**으로 영상의 실질 정보를 보존한다. 개수와 원문 대비 글자 비율로 잘라내지 않는다. 장황한 반복과 인사는 줄이되 새로운 정보는 버리지 않는다.

## 출력 스키마

```json
{
  "schema": "v3",
  "content_type": "market_brief | interview | deep_analysis | explainer | news_digest | entertainment | clip",
  "tldr": "한 문장 결론. 누가 + 무엇을 주장/결정 + 핵심 근거 1개. 120자 이내",
  "watch_guide": {"verdict": "skip | skim | watch", "why": "1~2문장. 요약으로 충분한지, 원본에서 볼 구간(ts)"},
  "key_points": [
    {"id": "k1", "point": "주장 한 줄(40자 이내)", "detail": "근거·수치·맥락·조건을 빠짐없이, 각 독립 요점은 줄바꿈으로 구분", "ts": "H:MM:SS", "quote": "근거 발화 원문 1개(150자 이내, 선택)"}
  ],
  "positions": [
    {"asset": "종목/자산", "action": "buy|sell|add|reduce|hold|plan_buy|plan_sell", "when": "done|today|conditional",
     "condition": "조건부일 때만", "detail": "평단·비중 등", "speaker": "이름|null", "ts": "", "quote": "필수"}
  ],
  "scenarios": [ {"if": "조건", "then": "화자가 말한 결과/대응", "ts": ""} ],
  "numbers":   [ {"fact": "검증·재인용 가능한 수치 1개", "ts": ""} ],
  "terms":     [ {"term": "", "explain": "뜻·맥락·영상 속 예시를 충분히", "source": "영상|보충"} ],
  "takeaways": [ {"type": "rule|counter|reference", "text": "", "ts": ""} ],
  "chapters":  [ {"ts": "", "title": "20자 내외"} ],
  "entities":  ["정규화된 종목·지수·인물명 — 검색/필터용"],
  "open_questions": ["화자가 판단 유보했거나 확인이 필요한 것"]
}
```

## 학습 본문 reading_guide — 경제 영상은 필수

**목표: 독자가 영상 전체를 보았을 때 얻을 배움·화자의 관점·경제 배경지식을 글만 읽고 이해하게 한다.** key_points를 문장만 늘려 복제하지 않는다. 원문 처음부터 끝까지 읽은 다음 주장마다 이유, 근거·사례, 조건·반론을 연결한다. 주제 수·본문 글자 수 상한은 없다. 짧은 요약은 이 본문의 대체재가 아니다.

v3 JSON에 아래 키를 추가한다. 기존 다른 필드는 유지한다.
```json
"reading_guide": {
  "version": 1,
  "title": "영상 전체를 관통하는 학습 주제",
  "introduction": "논의의 출발점과 서로 다른 화자의 관점을 연결하는 안내",
  "topics": [{
    "id": "topic-1", "title": "구체적인 소제목", "ts": "원문 시작 시간", "speaker": "해당 관점의 화자",
    "points": ["주장과 그 이유", "설명에 쓰인 실제 사례·숫자", "조건·예외·반론과 답변"],
    "background": ["보충 설명: 개념의 뜻 → 작동 원리 → 이 영상에서 왜 필요한지. 초보자도 논의를 따라가게"],
    "takeaways": ["이 사례에서 배워 다른 상황에도 쓸 수 있는 사고방식. 수익을 보장하는 법칙으로 바꾸지 않는다"],
    "caveats": ["화자의 해석과 확인된 사실이 다른 부분, 자막 오류, 미확인 주장을 정확히 구분"]
  }],
  "perspectives": [{"name":"화자", "view":"이 사람이 사안을 바라보는 틀과 근거", "watch":"해석할 때 빠뜨리면 안 되는 조건·한계"}],
  "lessons": ["영상을 끝까지 읽고 가져갈 질문과 지식"],
  "sources": [{"label":"보충 설명의 공식 근거", "url":"https://..."}],
  "coverage": {"transcript_lines":0,"read_lines":0,"excluded":"학습과 무관해 제외한 음악·광고·인사 등. 경제 주제는 생략 금지"}
}
```

- title 아래 points를 글머리표로 읽는다. 각 항목은 독립된 요점이면서 근거·맥락을 충분히 담는다.
- 과거 투자 경험, 실패 사례, 비유, 반문, 논쟁, 시청자 권유도 배울 것이 있으면 포함한다.
- 발언 중 잘못된 경제 설명은 그대로 교재의 사실로 옮기지 않는다. 화자의 주장으로 귀속하고, 배경란에서 공식 자료로 바로잡는다.
- 익숙한 용어라도 해당 논리를 이해하는 데 필요하면 설명한다. 용어 5개 제한이나 ‘일반 용어 금지’는 없다.
- 실제 읽은 줄 수와 파일 전체 줄 수를 적는다. 숫자를 맞추는 것이 전수 독해의 대체재는 아니다.
- 예시 정본: `web/content/reading-guides/WtEo31SpSeI.json` (676줄 전수 읽기, 13개 주제). 예시의 길이·주제 수를 상한으로 삼지 않는다.

## 핵심 규칙 (v2 대비 변경점)

1. **짧은 요약과 학습 본문은 별개다.** tldr·key_points는 빠르게 읽는 개요이고 reading_guide는 영상 전체의 논리·관점·배울 점을 이해할 본문이다. 같은 사실이 개요와 본문에 다시 나오는 것은 허용한다. 본문 안에서 의미 없는 반복만 줄이고, 다른 섹션에 썼다는 이유로 필요한 맥락을 생략하지 않는다.
2. **positions는 화자 본인의 실제 매매·계획만.** quote 안에 매매 동사(샀/팔/담/줄였/정리/손절/들어갔)나 계획 표현(사 볼까/팔고)이 있어야 한다. "좋아 보인다", "유튜버가 추천"은 key_points로. 시청자 권유는 따로 섹션을 만들지 않고 key_points 또는 scenarios에 넣는다(v2 action_items 폐지 — 47%가 다른 섹션과 같은 quote 재사용).
3. **content_type이 섹션을 고른다.**
   - market_brief / deep_analysis / interview: 전 섹션 가능
   - explainer / news_digest: positions·scenarios는 화자가 명시했을 때만. 대부분 key_points + numbers + terms + takeaways
   - entertainment / clip(3분 미만): tldr + key_points + watch_guide. 나머지는 생략(빈 배열 금지, 키 자체를 뺀다)
   - 경제와 무관한 회차는 억지로 경제 섹션을 채우지 말고 tldr에 그 사실을 적는다.
4. **정보 보존**: key_points·numbers·terms·takeaways·chapters에 개수 상한을 두지 않는다. 주제별 새로운 주장·근거·수치·예외·비교 사례를 보존한다. 긴 라이브는 주제별로 여러 key_points를 쓴다. detail은 독립 요점마다 줄바꿈하고, 조건과 결론을 서로 떨어뜨려 오해하게 만들지 않는다. 총 글자 수 25% 제한 폐지.

5. **quote는 근거 1개만.** 항목당 quote 최대 1개, 150자 이내, transcript 원문 그대로(STT 오류 포함). 여러 줄을 "..."로 이어 붙이지 않는다. 같은 quote를 두 항목에 쓰지 않는다. numbers·terms·takeaways·chapters·scenarios는 quote 없이 ts만.
6. **모델 추론 금지 구역**: quote나 transcript에 없는 연도·이름·수치를 보태지 않는다. 화자가 말하지 않은 시청자 권고를 만들지 않는다. 보충 지식은 terms의 `source:"보충"` 또는 reading_guide.topics[].background에서만 허용. 화자의 주장과 구분하고 근거 자료를 sources에 적는다.
7. **후반부 커버리지**: chapters의 마지막 ts가 영상 길이의 85% 이후여야 한다. 아니면 전수 Read가 안 된 것이므로 다시 읽는다.

## 저장 전 자체 검증 (save_summary.py가 기계 검증한다)
- 모든 quote가 transcript에 부분 문자열로 존재하는가
- 각 주제의 주장·근거·조건·반론·핵심 수치를 모두 포함했는가. 개수/글자 수를 맞추려고 삭제한 정보가 없는가
- 같은 quote 중복 0, numbers.fact가 key_points.detail에 그대로 있지 않은가
- chapters 마지막 ts ≥ 영상 길이 × 0.85

## 전수 Read 의무

라이브 영상은 1,500~3,000줄 규모가 흔하다. `read_chunks` 횟수만큼 offset/limit으로 분할 Read해 **끝까지** 읽기 전에는 JSON을 만들지 않는다. 핵심 매매·결론 발언은 후반부(70%~끝)에 몰려 있는 경우가 많다.

## 저장

만든 JSON을 `scripts/save_summary.py <vid>` stdin으로 전달한다. `schema: "v3"`이면 위 "저장 전 자체 검증" 항목을 기계 검증하고, 어긋나면 저장하지 않고 위반 목록을 stderr로 낸다. 고쳐서 다시 저장한다.

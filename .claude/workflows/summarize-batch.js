export const meta = {
  name: 'summarize-batch',
  description: '밀린 유튜브 주식·경제 요약을 최근순으로 다중 에이전트 병렬 처리',
  whenToUse: '요약 대기열(transcripts.summary IS NULL)이 쌓였을 때. args: {fanout, perAgent, rounds}',
  phases: [
    { title: 'Summarize', detail: '에이전트별 N건씩 claim→전수 Read→13섹션 JSON→저장' },
  ],
}

const ROOT = '/Users/ram/programming/vibecoding/youtubeScript'

const FANOUT = args?.fanout ?? 12      // 라운드당 동시 에이전트 수
const PER_AGENT = args?.perAgent ?? 4  // 에이전트 1명이 처리할 영상 수
const ROUNDS = args?.rounds ?? 4       // 라운드 반복 횟수

const RESULT_SCHEMA = {
  type: 'object',
  properties: {
    done: { type: 'integer', description: '실제로 요약을 저장한 영상 수' },
    screened: { type: 'integer', description: 'screened_out 처리한 영상 수' },
    empty: { type: 'boolean', description: '큐가 비어 더 가져올 영상이 없었으면 true' },
    titles: { type: 'array', items: { type: 'string' }, description: '처리한 영상 제목들' },
  },
  required: ['done', 'screened', 'empty'],
  additionalProperties: false,
}

const AGENT_PROMPT = `당신은 유튜브 주식·경제 transcript 요약 작업자입니다.
아래 절차를 최대 ${PER_AGENT}회 반복합니다. 작업 디렉토리: ${ROOT}

요약 범위는 채널 정책이 정한다(경제 30일 / 교양 제한없음) — 별도 환경변수를 붙이지 마라.

0. 최초 1회만: ${ROOT}/prompts/summary-guidelines.md 를 Read 한다.
   (출력 JSON 스키마 13섹션 · quotes verbatim 규칙 · 추출 규칙의 정본이다.)

각 회차:

1. 대상 1편 claim:
   cd ${ROOT} && source .env.local && .venv/bin/python scripts/get_next_unsummarized.py
   stdout의 마지막 JSON 라인을 파싱한다.
   - {"empty": true} 이면 즉시 중단하고 지금까지의 결과를 반환한다 (empty=true로 보고).
   - 정상이면 vid / channel_slug / title / transcript_path / transcript_lines / chunk_size / read_chunks 를 얻는다.

2. 스크리닝 (channel_slug가 jisik_inside 또는 yonhap_economy 일 때만):
   제목 + transcript 첫 청크만 보고 주식·경제 요약 가치를 판정한다.
   - 유지: 종목/매크로/경제정책/투자전략/시장분석 + 구체적 인사이트가 있는 영상
   - 제외: 일반 자기계발·인물 인생사·건강·군사·연예·단순 시황 반복중계·기관 원본 브리핑 등
   제외 판정이면
   cd ${ROOT} && source .env.local && .venv/bin/python scripts/screen_out.py <vid> "<사유>"
   를 실행하고 이 영상은 요약하지 않는다. screened 카운트를 1 올리고 다음 회차로 간다.

3. transcript 전수 Read (건너뛰기 금지):
   transcript_path를 Read 도구로 offset/limit을 써서 read_chunks회 나눠 **끝까지** 읽는다.
   i번째: offset = i * chunk_size + 1, limit = chunk_size.
   라이브 영상은 1,500~3,000줄까지 간다. 마지막 청크까지 읽지 않은 상태로 JSON을 만들지 않는다.

4. 가이드라인의 13섹션 JSON을 만든다.
   - 모든 청크에서 발화 인용을 골고루 추출한다. 핵심 매매 발언은 후반부에 몰려 있을 수 있다.
   - quotes는 transcript 원문 발화 그대로 + 라인 앞 타임스탬프 그대로.
   - "_model": "claude-opus-5" 를 포함한다.

5. 저장:
   Write 도구로 JSON을 /tmp/summary_<vid>.json 에 쓴 뒤
   cd ${ROOT} && source .env.local && cat /tmp/summary_<vid>.json | .venv/bin/python scripts/save_summary.py <vid>
   "saved: <vid>" 출력을 확인한다. 저장에 실패하면 done 카운트를 올리지 않는다.

반환값: done(저장 성공 건수), screened(스크린아웃 건수), empty(큐가 비었으면 true), titles(처리한 제목 목록).
사용자에게 말을 거는 대신 반환값만 정확히 채운다.`

phase('Summarize')

let totalDone = 0
let totalScreened = 0
const allTitles = []

for (let r = 0; r < ROUNDS; r++) {
  const results = await parallel(
    Array.from({ length: FANOUT }, (_, i) => () =>
      agent(AGENT_PROMPT, {
        label: `sum:r${r + 1}-a${i + 1}`,
        phase: 'Summarize',
        schema: RESULT_SCHEMA,
      })
    )
  )

  // agent()는 사용자가 중단시키거나 terminal error가 나면 null을 반환한다.
  const ok = results.filter(Boolean)
  const roundDone = ok.reduce((s, x) => s + (x.done || 0), 0)
  const roundScreened = ok.reduce((s, x) => s + (x.screened || 0), 0)
  totalDone += roundDone
  totalScreened += roundScreened
  for (const x of ok) if (Array.isArray(x.titles)) allTitles.push(...x.titles)

  log(
    `라운드 ${r + 1}/${ROUNDS}: 요약 +${roundDone} (누적 ${totalDone}), ` +
    `스크린아웃 +${roundScreened} (누적 ${totalScreened}), 에이전트 ${ok.length}/${FANOUT} 응답`
  )

  if (ok.length && ok.every((x) => x.empty)) {
    log('요약 대기열이 비었다 — 조기 종료')
    break
  }
}

return { totalDone, totalScreened, titles: allTitles }

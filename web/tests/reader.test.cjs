const assert = require('node:assert/strict')
const { test } = require('node:test')
const fs = require('node:fs')
const path = require('node:path')
const Module = require('node:module')
const ts = require('typescript')
const React = require('react')
const { renderToStaticMarkup } = require('react-dom/server')

// Next 서버 없이도 실제 컴포넌트의 HTML 보존 여부를 검사한다.
for (const extension of ['.ts', '.tsx']) {
  require.extensions[extension] = (module, filename) => {
    const source = ts.transpileModule(fs.readFileSync(filename, 'utf8'), {
      compilerOptions: { jsx: ts.JsxEmit.ReactJSX, module: ts.ModuleKind.CommonJS, esModuleInterop: true },
    }).outputText
    module._compile(source, filename)
  }
}
const resolve = Module._resolveFilename
Module._resolveFilename = function (request, ...rest) {
  return resolve.call(this, request.startsWith('@/') ? path.join(__dirname, '..', request.slice(2)) : request, ...rest)
}
const { SummaryCard } = require('../components/SummaryCard.tsx')
const { splitSentences, splitHeadline, isHeadlineMeta, splitNarrative, narrativeHeading } = require('../components/reader/text.ts')
const { youtubeJumpUrl } = require('../lib/timestamp.ts')
const render = (summary, channel) => renderToStaticMarkup(React.createElement(SummaryCard, { vid: 'sample-video', summary, channel }))
const plain = html => html.replace(/<[^>]*>/g, '').replaceAll('&#x27;', "'").replaceAll('&quot;', '"').replaceAll('&amp;', '&').replaceAll('&lt;', '<').replaceAll('&gt;', '>')
const quote = label => [{ timestamp: '1:02:03', text: `${label}의 근거 원문. 수치는 5.27%임.` }]
const fixture = {
  headline: '금리와 실적 / 투자 판단 — 변동성 확인',
  raw_summary: '금리는 5.27%다.실적을 확인함. 분산이 필요함. 현금도 자산임. 변동성이 남아 있음. 여섯 번째 핵심 정보다. 마지막 정보도 보존한다.',
  narrative: '[00:00~05:30] 시장 도입: 상황을 설명한다. 배경도 확인한다. → [05:30–12:00] 다음 주제: 기업 실적과 전망.',
  verdicts: [{ condition: '조건 원문', consequence: '결론 원문', speaker: '화자 A', quotes: quote('결론') }],
  buys: Array.from({ length: 7 }, (_, i) => ({ ticker: `매수종목 ${i}`, reason: `매수이유 ${i}. 두 번째 문장 ${i}.`, speaker: `매수화자 ${i}`, quotes: quote(`매수 ${i}`) })),
  sells: [{ ticker: '매도종목', reason: '매도이유', speaker: '매도화자', quotes: quote('매도') }],
  macro_views: [{ topic: '거시주제', view: '거시전망', speaker: '거시화자', quotes: quote('거시') }],
  chart_levels: [{ ticker: '차트종목', level: '123.45~150.50 지지선', reason: '차트이유', speaker: '차트화자', quotes: quote('차트') }],
  watchlist: [{ topic: '관전주제', reason: '관전이유', speaker: '관전화자', quotes: quote('관전') }],
  lessons: [{ type: 'counter', lesson: '교훈 원문', speaker: '교훈화자', quotes: quote('학습') }],
  data_points: [{ datum: '통계숫자 5.27%', quotes: quote('통계') }],
  action_items: [{ action: '실행계획', speaker: '실행화자', quotes: quote('실행') }],
  terms: ['영상', '보충', '영상+보충'].map(source => ({ term: `용어 ${source}`, explain: `설명 ${source}`, context: `맥락 ${source}`, source, quotes: quote(`용어 ${source}`) })),
}

test('한국어 종결·소수점·영문 약어·공백 없는 종결을 분리한다', () => {
  assert.deepEqual(splitSentences('5.27%다.상승함. 관망임. 위험이 남아 있음. Next point. U.S. 주식 3.14%.'),
    ['5.27%다.', '상승함.', '관망임.', '위험이 남아 있음.', 'Next point.', 'U.S.', '주식 3.14%.'])
  assert.deepEqual(splitHeadline('금리 / 실적—현금'), ['금리', '실적', '현금'])
  assert.deepEqual(splitHeadline('채널 속보 — 금리 5.27% / 실적 상승 | 현금 유지'), ['채널 속보', '금리 5.27%', '실적 상승', '현금 유지'])
  assert.deepEqual(splitHeadline('S&P500 / USD/KRW 1,350'), ['S&P500', 'USD/KRW 1,350'])
  assert.equal(splitNarrative(fixture.narrative).length, 2)
  assert.deepEqual(narrativeHeading('[00:00~05:30] 도입'), { time: '00:00~05:30', title: '도입' })
})

test('모든 JSON 텍스트·인용·여섯 번째 이후 항목을 서버 HTML에 보존한다', () => {
  const html = render(fixture)
  const text = plain(html)
  const verify = (value, key) => {
    if (typeof value === 'string') {
      const pieces = key === 'headline' ? splitHeadline(value) : key === 'narrative' ? splitNarrative(value) : [value]
      for (const piece of pieces.flatMap(splitSentences)) assert.ok(text.includes(piece), `누락: ${key} = ${piece}`)
    } else if (Array.isArray(value)) value.forEach(item => verify(item, key))
    else if (value) Object.entries(value).forEach(([k, v]) => verify(v, k))
  }
  verify(fixture)
  assert.ok(html.includes('2개 더 보기'))
  const buys = html.split('<section id="buys"')[1].split('</section>')[0]
  const [firstPage, remaining] = buys.split('<details class="reader-more')
  assert.ok(firstPage.includes('매수종목 4'))
  assert.ok(!firstPage.includes('매수종목 5'))
  assert.ok(remaining.includes('매수종목 5') && remaining.includes('매수종목 6'))
  assert.ok(html.includes('href="' + youtubeJumpUrl('sample-video', '1:02:03').replaceAll('&', '&amp;') + '"'))
  assert.doesNotMatch(html, /<details[^>]*\sopen(?:=|\s|>)/)
  const ids = [...html.matchAll(/<section id="([^"]+)"/g)].map(match => match[1])
  assert.deepEqual(ids, ['overview', 'verdicts', 'narrative', 'buys', 'sells', 'macro', 'chart', 'watchlist', 'lessons', 'data', 'actions', 'terms'])
})

test('빈 섹션을 생략하며 제목만 있는 요약과 미요약도 표시한다', () => {
  assert.doesNotMatch(render({ buys: [], terms: [] }), /<section|<nav/)
  assert.ok(render({ headline: '제목만 있는 요약' }).includes('제목만 있는 요약'))
  assert.ok(render(null).includes('아직 요약되지 않았어요.'))
})

test('긴 원문은 전체 요약 읽기에 기본 접힘으로 보존하며 임의 강조를 제거한다', () => {
  const sentence = '긴 설명과 수치를 보존하기 위해서 사용되는 문장으로 금리는 5.27%이며 정보가 누락되지 않아야 하고 문장의 끝에 있는 중요한 내용과 근거까지도 모두 남아 있어야 한다. '.repeat(4)
  const html = render({ raw_summary: sentence })
  assert.doesNotMatch(html, /<strong|<b\b|<section/)
  assert.match(html, /<details class="reader-full-summary[^>]*><summary[^>]*>전체 요약 읽기/)
  assert.doesNotMatch(html, /<details[^>]*\sopen(?:=|\s|>)/)
  assert.ok(html.indexOf(sentence.slice(0, 20)) > html.indexOf('</summary>'))
  for (const part of splitSentences(sentence)) assert.ok(plain(html).includes(part))
  const css = fs.readFileSync(path.join(__dirname, '../app/globals.css'), 'utf8')
  assert.match(css, /\.summary-body \.reader-sentences span\s*\{\s*line-height: 1\.7;/)
})

test('핵심 포인트는 잘리지 않는 헤드라인과 상위 세 결론만 표시한다', () => {
  const verdicts = Array.from({ length: 4 }, (_, i) => ({ condition: `조건 ${i}`, consequence: `결과 ${i}` }))
  const summary = { headline: '채널 주말 속보 — 고용 하회에도 美 10년 5.27% 상승 / 나스닥 +1% | 변동성 확인', raw_summary: '긴 전체 요약에만 있는 내용.', verdicts }
  const html = render(summary, '채널')
  const overview = html.split('<section id="overview"')[1].split('</section>')[0]
  assert.match(overview, /<p class="mb-2 text-xs text-zinc-400">채널 주말 속보<\/p>/)
  assert.equal((overview.match(/<li\b/g) ?? []).length, 6)
  assert.doesNotMatch(overview, /truncate|line-clamp|<details|<summary|<button|⌄|긴 전체 요약|조건 3/)
  for (const point of splitHeadline(summary.headline)) assert.ok(plain(overview).includes(point))
  for (let i = 0; i < 3; i++) assert.ok(plain(overview).includes(`조건 ${i} → 결과 ${i}`))
  assert.ok(plain(html).includes('조건 3'))
  assert.ok(html.indexOf('reader-full-summary') > html.indexOf('</section>'))
  assert.ok(render({ verdicts }).includes('핵심 포인트'))
})

test('짧다는 이유만으로 실제 정보를 채널 메타로 취급하지 않는다', () => {
  assert.equal(isHeadlineMeta('금리 인하'), false)
  assert.equal(isHeadlineMeta('금리 인하', '채널'), false)
  assert.equal(isHeadlineMeta('채널 주말 속보', '채널'), true)
  assert.equal(isHeadlineMeta('채널의 길고 상세한 경제 분석', '채널'), false)
})

test('항목 설명과 부가 정보는 합쳐서 두 줄 미리보기이며 원문과 근거는 접힌다', () => {
  const html = render(fixture)
  const chart = html.split('<section id="chart"')[1].split('</section>')[0]
  const preview = chart.split('<summary')[1].split('</summary>')[0]
  assert.equal((preview.match(/line-clamp-2/g) ?? []).length, 1)
  assert.match(preview, /truncate/)
  assert.ok(plain(preview).includes('차트이유 · 123.45~150.50 지지선'))
  const expanded = chart.slice(chart.indexOf('</summary>') + '</summary>'.length)
  assert.ok(plain(expanded).includes('차트이유'))
  assert.ok(plain(expanded).includes('123.45~150.50 지지선'))
  assert.match(expanded, /<details class="reader-quotes">/)
  assert.ok(plain(expanded).includes('차트의 근거 원문.'))
  assert.doesNotMatch(html, /<strong|<details[^>]*\sopen(?:=|\s|>)/)
})


test('피드는 경량 응답·전체 요약·검색 근거를 유지하고 개수 칩은 제거한다', () => {
  const { VideoCard } = require('../components/VideoCard.tsx')
  const { getMatchReasons } = require('../lib/matchReason.ts')
  const transcript = {
    vid: 'feed-video', channel: '테스트 채널', channel_slug: 'test-channel', title: '엔비디아 실적 분석',
    published_at: '2026-10-05', summarized_at: null, headline: '경량 헤드라인', n_buys: 7,
  }
  const light = renderToStaticMarkup(React.createElement(VideoCard, { t: transcript }))
  assert.ok(light.includes('경량 헤드라인'))
  assert.ok(light.includes('2026-10-05'))
  assert.doesNotMatch(plain(light), /매수 7/)
  const full = { ...transcript, summary: { headline: '전체 헤드라인', buys: [{ ticker: '삼성전자', reason: '저평가 매수', speaker: null, quotes: [] }] } }
  const searched = renderToStaticMarkup(React.createElement(VideoCard, { t: full, searchQuery: '삼성전자' }))
  assert.ok(searched.includes('전체 헤드라인'))
  assert.ok(searched.includes('<mark'))
  assert.equal(getMatchReasons(full, '삼성전자')[0].label, '매수 코멘트')
  assert.deepEqual(getMatchReasons(full, '존재안함토큰'), [])
})

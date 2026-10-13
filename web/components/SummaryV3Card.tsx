import { NumericFact } from './reader/NumericFact'
import { ReadingGuide } from './ReadingGuide'
import type { ReactNode } from 'react'
import type { SummaryV3 } from '@/lib/supabase'
import { youtubeJumpUrl } from '@/lib/timestamp'
import { QuoteList } from './QuoteList'
import { ReaderNav } from './reader/ReaderNav'
import {
  LimitedList,
  ReadableText,
  SectionHeading,
  SentenceList,
} from './reader/ReaderPrimitives'

const actions = {
  buy: ['매수', 'buy'],
  add: ['추가매수', 'buy'],
  plan_buy: ['매수 계획', 'buy'],
  sell: ['매도', 'sell'],
  reduce: ['비중축소', 'sell'],
  plan_sell: ['매도 계획', 'sell'],
  hold: ['보유', 'hold'],
} as const
const verdicts = {
  skip: '요약으로 충분해요',
  skim: '필요한 부분만 보세요',
  watch: '원본도 볼 만해요',
}
const takeawayTypes = {
  rule: '기억할 원칙',
  counter: '다른 관점',
  reference: '참고할 내용',
  analogy: '이해를 돕는 비유',
}
const timings: Record<string, string> = {
  done: '실행 완료',
  conditional: '조건부',
  now: '현재',
  planned: '예정',
}

export function SummaryV3Card({
  vid,
  summary,
}: {
  vid: string
  summary: SummaryV3
}) {
  const time = (ts?: string) =>
    ts ? (
      <a
        href={youtubeJumpUrl(vid, ts)}
        target="_blank"
        rel="noreferrer"
        aria-label={`${ts}부터 YouTube에서 재생`}
        className="time-link"
      >
        {ts} <span aria-hidden="true">↗</span>
      </a>
    ) : null
  const quote = (text?: string, ts?: string) =>
    !text ? null : ts ? (
      <QuoteList vid={vid} quotes={[{ timestamp: ts, text }]} />
    ) : (
      <details className="reader-quotes" open>
        <summary>
          <span className="quote-symbol" aria-hidden="true">
            “
          </span>
          실제로 한 말{' '}
          <span aria-hidden="true" className="disclosure-arrow">
            ⌄
          </span>
        </summary>
        <div className="quote-content">
          <SentenceList text={text} />
        </div>
      </details>
    )
  const sections: {
    id: string
    title: string
    nav?: string
    description: string
    items: ReactNode[]
  }[] = [
    {
      id: 'positions',
      title: '매수·매도 발언',
      nav: '매수·매도',
      description: '출연자의 발언을 모았어요. 계획과 실행을 구분해 읽어보세요.',
      items:
        summary.positions?.map((p, i) => (
          <div
            key={i}
            className={`position-card tone-${actions[p.action]?.[1] ?? 'hold'}`}
          >
            <div className="item-topline">
              <span
                className={`signal signal-${actions[p.action]?.[1] ?? 'hold'}`}
              >
                {actions[p.action]?.[0] ?? p.action}
              </span>
              {p.when && (
                <span className="item-status">{timings[p.when] ?? p.when}</span>
              )}
              {time(p.ts)}
            </div>
            <h3 className="asset-name">{p.asset}</h3>
            {p.speaker && <p className="speaker-label">발언 · {p.speaker}</p>}
            {p.condition && (
              <div className="condition-box">
                <span>이 조건에서</span>
                <ReadableText text={p.condition} />
              </div>
            )}
            {p.detail && <ReadableText text={p.detail} />}
            {quote(p.quote, p.ts)}
          </div>
        )) ?? [],
    },
    {
      id: 'key-points',
      title: '핵심 주장과 이유',
      nav: '핵심 내용',
      description: '주장과 그 이유를 함께 읽어요.',
      items:
        summary.key_points?.map((p, i) => (
          <div key={p.id} className="insight-card">
            <div className="item-topline">
              <span className="item-number">
                {String(i + 1).padStart(2, '0')}
              </span>
              {time(p.ts)}
            </div>
            <h3>{p.point}</h3>
            {p.detail && <ReadableText text={p.detail} />}
            {quote(p.quote, p.ts)}
          </div>
        )) ?? [],
    },
    {
      id: 'scenarios',
      title: '조건별 전망',
      nav: '관전 포인트',
      description: '방송에서 제시한 조건과 예상이에요.',
      items:
        summary.scenarios?.map((p, i) => (
          <div key={i} className="scenario-card">
            <div>
              <span className="small-label">이런 일이 생기면</span>
              <ReadableText text={p.if} />
            </div>
            <span className="scenario-arrow" aria-hidden="true">
              ↓
            </span>
            <div>
              <span className="small-label">출연자의 예상</span>
              <ReadableText text={p.then} />
            </div>
            {time(p.ts)}
          </div>
        )) ?? [],
    },
    {
      id: 'terms',
      title: '용어와 배경지식',
      nav: '경제 용어',
      description: '낯선 말은 뜻과 맥락을 함께 확인해요.',
      items:
        summary.terms?.map((p, i) => (
          <div key={i} className="term-card">
            <span className="term-index">{String(i + 1).padStart(2, '0')}</span>
            <div>
              <h3>{p.term}</h3>
              <ReadableText text={p.explain} />
              {p.context && (
                <div className="term-context">
                  <span>영상 속 맥락</span>
                  <ReadableText text={p.context} />
                </div>
              )}
              {p.source && (
                <span className="source-label">
                  {p.source === '보충'
                    ? '이해를 위한 보충 설명'
                    : p.source === '영상+보충'
                      ? '영상 내용 + 보충 설명'
                      : '영상에서 설명한 개념'}
                </span>
              )}
              <QuoteList vid={vid} quotes={p.quotes} />
            </div>
          </div>
        )) ?? [],
    },
    {
      id: 'takeaways',
      title: '다음에도 써먹을 경제 지식',
      nav: '배울 점',
      description: '한 번의 시황을 넘어 기억할 이야기.',
      items:
        summary.takeaways?.map((p, i) => (
          <div key={i} className="lesson-card">
            <div className="item-topline">
              <span className="small-label">
                {takeawayTypes[p.type] ?? p.type}
              </span>
              {time(p.ts)}
            </div>
            <ReadableText text={p.text} />
          </div>
        )) ?? [],
    },
    {
      id: 'numbers',
      title: '주요 수치와 기준',
      nav: '주요 숫자',
      description: '방송에서 언급한 수치예요. 기준 시점을 함께 확인하세요.',
      items:
        summary.numbers?.map((p, i) => (
          <div key={i} className="number-card">
            <NumericFact text={p.fact} />
            {time(p.ts)}
          </div>
        )) ?? [],
    },
    {
      id: 'chapters',
      title: '원본에서 찾아보기',
      nav: '영상 목차',
      description: '궁금한 주제를 고르면 해당 시간으로 이동해요.',
      items:
        summary.chapters?.map((p, i) => (
          <a
            key={i}
            className="chapter-row"
            href={youtubeJumpUrl(vid, p.ts)}
            target="_blank"
            rel="noreferrer"
          >
            <span className="chapter-time">{p.ts}</span>
            <span>{p.title}</span>
            <span className="chapter-play" aria-hidden="true">
              ↗
            </span>
          </a>
        )) ?? [],
    },
    {
      id: 'entities',
      title: '언급된 기업·인물',
      nav: '주요 대상',
      description: '방송에 등장한 기업과 인물.',
      items:
        summary.entities?.map((p, i) => (
          <span key={i} className="entity-tag">
            {p}
          </span>
        )) ?? [],
    },
    {
      id: 'open-questions',
      title: '아직 남은 질문',
      nav: '남은 질문',
      description: '요약만으로 답이 정해지지 않은 부분이에요.',
      items:
        summary.open_questions?.map((p, i) => (
          <div key={i} className="question-card">
            <span aria-hidden="true">?</span>
            <ReadableText text={p} />
          </div>
        )) ?? [],
    },
  ].filter((s) => s.items.length > 0)

  return (
    <div className="summary-body">
      <section
        id="overview"
        aria-labelledby="overview-heading"
        className="overview-card"
      >
        <p className="eyebrow">THE BRIEF</p>
        <h2 id="overview-heading">먼저, 한눈에</h2>
        <ReadableText text={summary.tldr} limit={260} />
        {summary.watch_guide && (
          <div className="watch-guide">
            <span className="watch-verdict">
              {verdicts[summary.watch_guide.verdict] ?? '시청 안내'}
            </span>
            <ReadableText text={summary.watch_guide.why} />
          </div>
        )}
      </section>
      {(sections.length > 0 || summary.reading_guide) && (
        <>
          <ReaderNav
            sections={[
              { id: 'overview', title: '한눈에' },
              ...(summary.reading_guide
                ? [{ id: 'learning', title: '깊이 읽기' }]
                : []),
              ...sections.map((s) => ({ id: s.id, title: s.nav ?? s.title })),
            ]}
          />
          <div className="reader-sections">
            {summary.reading_guide && (
              <ReadingGuide guide={summary.reading_guide} />
            )}
            {sections.map((s) => (
              <section
                key={s.id}
                id={s.id}
                aria-labelledby={`${s.id}-heading`}
                className={`reader-section section-${s.id}`}
              >
                <SectionHeading
                  id={s.id}
                  title={s.title}
                  count={s.items.length}
                  description={s.description}
                />
                <LimitedList
                  items={s.items}
                  label={s.title}
                  compact={s.id === 'entities'}
                />
              </section>
            ))}
          </div>
        </>
      )}
    </div>
  )
}

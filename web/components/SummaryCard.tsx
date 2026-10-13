import { SummaryV3Card } from './SummaryV3Card'
import type { ReactNode } from 'react'
import type { Quote, Summary } from '@/lib/supabase'
import { ReaderNav } from './reader/ReaderNav'
import { QuoteList } from './QuoteList'
import {
  LimitedList,
  ReadableText,
  SentenceList,
  SectionHeading,
} from './reader/ReaderPrimitives'
import {
  isHeadlineMeta,
  narrativeHeading,
  splitHeadline,
  splitNarrative,
} from './reader/text'

type Props = { vid: string; summary: Summary | null; channel?: string }
type ReaderSection = {
  id: string
  title: string
  nav: string
  description: string
  items: ReactNode[]
}
const lessonTypes: Record<string, string> = {
  rule: '기억할 원칙',
  counter: '다른 관점',
  reference: '참고할 내용',
  analogy: '이해를 돕는 비유',
}

export function SummaryCard({ vid, summary, channel }: Props) {
  if (!summary)
    return (
      <div className="empty-state">
        <h2>요약을 준비하고 있어요</h2>
        <p>다른 영상의 요약을 먼저 읽어보세요.</p>
      </div>
    )
  if (summary.schema === 'v3')
    return <SummaryV3Card vid={vid} summary={summary} />
  const row = (
    title: string,
    body?: string,
    speaker?: string | null,
    quotes?: Quote[],
    badge?: string,
    extra?: string,
    tone = '',
  ) => (
    <ReaderItem
      vid={vid}
      title={title}
      body={body}
      speaker={speaker}
      quotes={quotes}
      badge={badge}
      extra={extra}
      tone={tone}
    />
  )
  const sections: ReaderSection[] = [
    {
      id: 'buys',
      title: '매수한다고 말한 것',
      nav: '매수 발언',
      description: '출연자가 밝힌 대상과 이유예요.',
      items:
        summary.buys?.map((it) =>
          row(
            it.ticker,
            it.reason,
            it.speaker,
            it.quotes,
            '매수',
            undefined,
            'buy',
          ),
        ) ?? [],
    },
    {
      id: 'sells',
      title: '매도한다고 말한 것',
      nav: '매도 발언',
      description: '어떤 이유로 줄이거나 팔았는지 확인해요.',
      items:
        summary.sells?.map((it) =>
          row(
            it.ticker,
            it.reason,
            it.speaker,
            it.quotes,
            '매도',
            undefined,
            'sell',
          ),
        ) ?? [],
    },
    {
      id: 'verdicts',
      title: '어떤 변화에 주목할까',
      nav: '관전 포인트',
      description: '출연자의 판단과 그 판단이 성립하는 조건.',
      items:
        summary.verdicts?.map((it) =>
          row(
            it.condition,
            it.consequence,
            it.speaker,
            it.quotes,
            '조건과 예상',
          ),
        ) ?? [],
    },
    {
      id: 'macro',
      title: '시장을 보는 큰 그림',
      nav: '시장 흐름',
      description: '금리·환율·경기 이야기를 연결해 읽어요.',
      items:
        summary.macro_views?.map((it) =>
          row(it.topic, it.view, it.speaker, it.quotes),
        ) ?? [],
    },
    {
      id: 'terms',
      title: '경제 용어, 여기서 이해하기',
      nav: '경제 용어',
      description: '낯선 말은 뜻과 맥락을 함께 확인해요.',
      items:
        summary.terms?.map((it, i) => (
          <div key={i} className="term-card">
            <span className="term-index">{String(i + 1).padStart(2, '0')}</span>
            <div>
              <h3>{it.term}</h3>
              <ReadableText text={it.explain} />
              {it.context && (
                <div className="term-context">
                  <span>영상 속 맥락</span>
                  <ReadableText text={it.context} />
                </div>
              )}
              {it.source && <span className="source-label">{it.source}</span>}
              <QuoteList vid={vid} quotes={it.quotes} />
            </div>
          </div>
        )) ?? [],
    },
    {
      id: 'lessons',
      title: '다음에도 써먹을 경제 지식',
      nav: '배울 점',
      description: '한 번의 시황을 넘어 기억할 이야기.',
      items:
        summary.lessons?.map((it) =>
          row(
            it.lesson,
            undefined,
            it.speaker,
            it.quotes,
            lessonTypes[it.type] ?? it.type,
          ),
        ) ?? [],
    },
    {
      id: 'watchlist',
      title: '앞으로 지켜볼 것',
      nav: '지켜볼 것',
      description: '방송에서 주목한 이슈와 다음 확인 지점.',
      items:
        summary.watchlist?.map((it) =>
          row(it.topic, it.reason, it.speaker, it.quotes),
        ) ?? [],
    },
    {
      id: 'chart',
      title: '차트에서 짚은 구간',
      nav: '가격 구간',
      description: '방송 시점의 가격 구간과 해석이에요.',
      items:
        summary.chart_levels?.map((it) =>
          row(it.ticker, it.reason, it.speaker, it.quotes, undefined, it.level),
        ) ?? [],
    },
    {
      id: 'data',
      title: '숫자로 짚어보기',
      nav: '주요 숫자',
      description: '방송에서 언급한 수치와 근거.',
      items:
        summary.data_points?.map((it) =>
          row(it.datum, undefined, undefined, it.quotes),
        ) ?? [],
    },
    {
      id: 'actions',
      title: '출연자가 제안한 행동',
      nav: '행동 제안',
      description: '발언자의 의견과 그 근거를 함께 읽어요.',
      items:
        summary.action_items?.map((it) =>
          row(it.action, undefined, it.speaker, it.quotes),
        ) ?? [],
    },
    {
      id: 'narrative',
      title: '영상 흐름 따라가기',
      nav: '영상 목차',
      description: '어떤 순서로 이야기가 이어졌는지 확인해요.',
      items: summary.narrative
        ? splitNarrative(summary.narrative).map((step, i) => {
            const { time, title } = narrativeHeading(step)
            return (
              <div key={i} className="reader-flow">
                <p className="chapter-time">{time || String(i+1).padStart(2,'0')}</p>
                <h3 className="flow-title">{title.split(/[:：]/u)[0]}</h3>
                <SentenceList text={step}/>
              </div>
            )
          })
        : [],
    },
  ].filter((s) => s.items.length > 0)
  const headlines = summary.headline ? splitHeadline(summary.headline) : []
  const meta =
    headlines[0] && isHeadlineMeta(headlines[0], channel)
      ? headlines.shift()
      : undefined
  const verdicts = summary.verdicts?.slice(0, 3) ?? []
  const hasOverview = Boolean(meta || headlines.length || verdicts.length)
  return (
    <div className="summary-body">
      {hasOverview && (
        <section
          id="overview"
          aria-labelledby="overview-heading"
          className="overview-card"
        >
          <p className="eyebrow">THE BRIEF</p>
          <h2 id="overview-heading">먼저, 한눈에</h2>
          {meta && <p className="source-label">{meta}</p>}
          {headlines.length > 0 ? (
            <ul className="overview-points">
              {headlines.map((p, i) => (
                <li key={i}>
                  <ReadableText text={p} limit={220} />
                </li>
              ))}
            </ul>
          ) : (
            <ul className="overview-points">
              {verdicts.map((v, i) => (
                <li key={i}>
                  <ReadableText text={`${v.condition} → ${v.consequence}`} />
                </li>
              ))}
            </ul>
          )}
        </section>
      )}
      {summary.raw_summary && (
        <details className="reader-full-summary" open>
          <summary>
            전체 요약 읽기{' '}
            <span aria-hidden="true" className="disclosure-arrow">
              ⌄
            </span>
          </summary>
          <SentenceList text={summary.raw_summary} />
        </details>
      )}
      {sections.length > 0 && (
        <>
          <ReaderNav
            sections={[
              ...(hasOverview ? [{ id: 'overview', title: '한눈에' }] : []),
              ...sections.map((s) => ({ id: s.id, title: s.nav })),
            ]}
          />
          <div className="reader-sections">
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
                <LimitedList items={s.items} label={s.title} />
              </section>
            ))}
          </div>
        </>
      )}
    </div>
  )
}

function ReaderItem({
  vid,
  title,
  body,
  speaker,
  quotes,
  badge,
  extra,
  tone,
}: {
  vid: string
  title: string
  body?: string
  speaker?: string | null
  quotes?: Quote[]
  badge?: string
  extra?: string
  tone?: string
}) {
  return (
    <div className={`insight-card ${tone ? `tone-${tone}` : ''}`}>
      {badge && (
        <span className={tone ? `signal signal-${tone}` : 'small-label'}>
          {badge}
        </span>
      )}
      <h3>{title}</h3>
      {speaker && <p className="speaker-label">발언 · {speaker}</p>}
      {body && <ReadableText text={body} />}{' '}
      {extra && (
        <div className="condition-box">
          <ReadableText text={extra} />
        </div>
      )}
      <QuoteList vid={vid} quotes={quotes} />
    </div>
  )
}

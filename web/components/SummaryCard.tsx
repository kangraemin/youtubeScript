import { SummaryV3Card } from './SummaryV3Card'
import type { ReactNode } from 'react'
import type { Quote, Summary } from '@/lib/supabase'
import { ReaderNav } from './reader/ReaderNav'
import { QuoteList } from './QuoteList'
import { LimitedList, SentenceList } from './reader/ReaderPrimitives'
import { isHeadlineMeta, narrativeHeading, splitHeadline, splitNarrative } from './reader/text'

type Props = { vid: string; summary: Summary | null; channel?: string }
type ReaderSection = { id: string; title: string; items: ReactNode[] }

export function SummaryCard({ vid, summary, channel }: Props) {
  if (!summary) return <p className="rounded-xl border border-zinc-800 p-6 text-sm text-zinc-400">아직 요약되지 않았어요.</p>

  if (summary.schema === 'v3') return <SummaryV3Card vid={vid} summary={summary} />

  const row = (title: string, body?: string, speaker?: string | null, quotes?: Quote[], badge?: string, extra?: string, signal = false) => (
    <ReaderItem vid={vid} title={title} body={body} speaker={speaker} quotes={quotes} badge={badge} extra={extra} signal={signal} />
  )
  const sections: ReaderSection[] = [
    { id: 'verdicts', title: '결론·시그널', items: summary.verdicts?.map(it => row(it.condition, it.consequence, it.speaker, it.quotes, undefined, undefined, true)) ?? [] },
    { id: 'narrative', title: '영상 흐름', items: summary.narrative ? splitNarrative(summary.narrative).map((step, i) => {
      const { time, title } = narrativeHeading(step)
      return <details className="reader-flow">
        <summary className="flex min-h-11 cursor-pointer items-center gap-3">
          <span className="shrink-0 font-mono text-xs text-sky-300">{time || String(i + 1).padStart(2, '0')}</span>
          <span className="min-w-0 flex-1 truncate text-sm font-medium text-zinc-100">{title}</span>
          <span aria-hidden="true" className="disclosure-arrow text-zinc-400">⌄</span>
        </summary>
        <div className="pb-2 pt-3"><SentenceList text={step} /></div>
      </details>
    }) : [] },
    { id: 'buys', title: '매수', items: summary.buys?.map(it => row(it.ticker, it.reason, it.speaker, it.quotes)) ?? [] },
    { id: 'sells', title: '매도', items: summary.sells?.map(it => row(it.ticker, it.reason, it.speaker, it.quotes)) ?? [] },
    { id: 'macro', title: '거시 진단', items: summary.macro_views?.map(it => row(it.topic, it.view, it.speaker, it.quotes)) ?? [] },
    { id: 'chart', title: '차트 자리', items: summary.chart_levels?.map(it => row(it.ticker, it.reason, it.speaker, it.quotes, undefined, it.level)) ?? [] },
    { id: 'watchlist', title: '봐야 할 것', items: summary.watchlist?.map(it => row(it.topic, it.reason, it.speaker, it.quotes)) ?? [] },
    { id: 'lessons', title: '학습 포인트', items: summary.lessons?.map(it => row(it.lesson, undefined, it.speaker, it.quotes, it.type)) ?? [] },
    { id: 'data', title: '통계·숫자', items: summary.data_points?.map(it => row(it.datum, undefined, undefined, it.quotes)) ?? [] },
    { id: 'actions', title: '실행 가능', items: summary.action_items?.map(it => row(it.action, undefined, it.speaker, it.quotes)) ?? [] },
    { id: 'terms', title: '용어', items: summary.terms?.map(it => row(it.term, it.explain, undefined, it.quotes, it.source, it.context)) ?? [] },
  ].filter(section => section.items.length > 0)
  const headlines = summary.headline ? splitHeadline(summary.headline) : []
  const meta = headlines[0] && isHeadlineMeta(headlines[0], channel) ? headlines.shift() : undefined
  const verdicts = summary.verdicts?.slice(0, 3) ?? []
  const hasOverview = Boolean(meta || headlines.length || verdicts.length)

  return <div className="summary-body min-w-0">
    {hasOverview && <section id="overview" aria-labelledby="overview-heading" className="mb-7 scroll-mt-24 border-l-4 border-[var(--accent)] pl-4">
      <h2 id="overview-heading" className="mb-3 text-lg font-semibold tracking-tight text-[var(--accent)]">핵심 포인트</h2>
      <div className="max-h-[65svh] overflow-y-auto" role="region" aria-label="핵심 포인트 목록" tabIndex={0}>
        {meta && <p className="mb-2 text-xs text-zinc-400">{meta}</p>}
        {headlines.length > 0 && <ul className="list-disc space-y-2 pl-4 text-sm text-zinc-200 marker:text-zinc-500">
          {headlines.map((point, i) => <li key={i}>{point}</li>)}
        </ul>}
        {verdicts.length > 0 && <ul className="mt-3 list-disc space-y-2 pl-4 text-sm text-zinc-300 marker:text-zinc-500">
          {verdicts.map((verdict, i) => <li key={i}>
            <span>{verdict.condition}</span>{' '}
            <span className={verdict.condition.length + verdict.consequence.length > 48 ? 'block' : ''}><span className="font-semibold text-[var(--accent)]">→</span> {verdict.consequence}</span>
          </li>)}
        </ul>}
      </div>
    </section>}

    {summary.raw_summary && <details className="reader-full-summary mb-7 border-y border-zinc-800">
      <summary className="flex min-h-11 cursor-pointer items-center justify-between gap-2 text-sm text-zinc-300">
        전체 요약 읽기
        <span aria-hidden="true" className="disclosure-arrow text-zinc-400">⌄</span>
      </summary>
      <div className="py-3"><SentenceList text={summary.raw_summary} /></div>
    </details>}

    {sections.length > 0 && <>
      <ReaderNav sections={[
        ...(hasOverview ? [{ id: 'overview', title: '핵심 포인트' }] : []),
        ...sections.map(({ id, title }) => ({ id, title })),
      ]} />
      <div className="space-y-9">
        {sections.map(section => <section key={section.id} id={section.id} aria-labelledby={`${section.id}-heading`} className="scroll-mt-24">
          <div className="mb-2 flex items-baseline gap-2 border-b border-zinc-700 pb-3">
            <h2 id={`${section.id}-heading`} className="text-lg font-semibold tracking-tight">{section.title}</h2>
            <span className="rounded bg-zinc-800 px-1.5 py-0.5 text-xs tabular-nums text-[var(--accent)]">{section.items.length}</span>
          </div>
          <LimitedList items={section.items} label={section.title} />
        </section>)}
      </div>
    </>}
  </div>
}

function ReaderItem({ vid, title, body, speaker, quotes, badge, extra, signal = false }: {
  vid: string; title: string; body?: string; speaker?: string | null; quotes?: Quote[]; badge?: string; extra?: string; signal?: boolean
}) {
  return <div className="min-w-0">
    <details className="reader-item">
      <summary className="min-h-11 cursor-pointer py-1">
        <span className="flex min-w-0 items-center gap-2">
          {signal && <span className="shrink-0 text-xs font-medium text-[var(--accent)]">조건</span>}
          <span className="min-w-0 flex-1 truncate text-[15px] font-semibold text-zinc-100">{title}</span>
          {badge && <span className="shrink-0 rounded border border-zinc-700 px-1.5 py-0.5 text-xs font-normal text-zinc-300">{badge}</span>}
          <span aria-hidden="true" className="disclosure-arrow shrink-0 text-zinc-400">⌄</span>
        </span>
        {speaker && <span className="block truncate text-xs text-zinc-400">{speaker}</span>}
        {(body || extra) && <span className="reader-preview mt-1 line-clamp-2 text-sm text-zinc-300">{signal && <span className="font-semibold text-[var(--accent)]">→ </span>}{[body, extra].filter(Boolean).join(' · ')}</span>}
      </summary>
      <div className="space-y-3 py-3">
        <SentenceList text={title} />
        {speaker && <p className="text-xs text-zinc-400">{speaker}</p>}
        {body && <SentenceList text={body} />}
        {extra && <SentenceList text={extra} />}
      </div>
    </details>
    <QuoteList vid={vid} quotes={quotes} />
  </div>
}

import type { ReactNode } from 'react'
import type { SummaryV3 } from '@/lib/supabase'
import { youtubeJumpUrl } from '@/lib/timestamp'
import { QuoteList } from './QuoteList'
import { ReaderNav } from './reader/ReaderNav'
import { LimitedList, SentenceList } from './reader/ReaderPrimitives'

const actions = {
  buy: ['매수', 'bg-emerald-950 text-emerald-300'],
  add: ['추가매수', 'bg-emerald-950 text-emerald-300'],
  plan_buy: ['매수 계획', 'bg-emerald-950 text-emerald-300'],
  sell: ['매도', 'bg-rose-950 text-rose-300'],
  reduce: ['비중축소', 'bg-rose-950 text-rose-300'],
  plan_sell: ['매도 계획', 'bg-rose-950 text-rose-300'],
  hold: ['보유', 'bg-zinc-800 text-zinc-300'],
} as const
const verdicts = { skip: '건너뛰기', skim: '훑기', watch: '볼 만함' }
const contentTypes: Record<string, string> = {
  market_brief: '시황', interview: '인터뷰', deep_analysis: '심층 분석',
  explainer: '해설', news_digest: '뉴스', entertainment: '엔터테인먼트', clip: '클립',
}
const takeawayTypes = { rule: '원칙', counter: '반론', reference: '참고', analogy: '비유' }
const timings: Record<string, string> = { done: '실행 완료', conditional: '조건부', now: '현재', planned: '예정' }

// 기본 화면은 정보마다 한 줄. 긴 내용은 펼쳐 문장 단위로 읽는다.
function Line({ text, small = false }: { text: string; small?: boolean }) {
  return <details className="reader-item min-w-0">
    <summary className={`cursor-pointer truncate py-1 ${small ? 'text-xs text-zinc-400' : 'text-sm text-zinc-200'}`} title={text}>{text}</summary>
    <div className="py-2"><SentenceList text={text} /></div>
  </details>
}

export function SummaryV3Card({ vid, summary }: { vid: string; summary: SummaryV3 }) {
  const time = (ts?: string) => ts ? <a href={youtubeJumpUrl(vid, ts)} target="_blank" rel="noreferrer"
    aria-label={`${ts}부터 YouTube에서 재생`}
    className="inline-flex min-h-11 shrink-0 items-center font-mono text-xs text-sky-300 hover:underline">{ts} ↗</a> : null
  const quote = (text?: string, ts?: string) => !text ? null : ts
    ? <QuoteList vid={vid} quotes={[{ timestamp: ts, text }]} />
    : <details className="reader-quotes">
      <summary className="flex min-h-11 cursor-pointer items-center gap-2 text-xs text-zinc-400"><span aria-hidden="true" className="disclosure-arrow">⌄</span>근거 발언 1개</summary>
      <div className="rounded-lg bg-zinc-900/70 p-3 sm:p-4"><SentenceList text={text} /></div>
    </details>
  const row = (text: string, ts?: string) => <div className="flex min-w-0 items-center gap-3">
    <div className="min-w-0 flex-1"><Line text={text} /></div>{time(ts)}
  </div>
  const sections: { id: string; title: string; items: ReactNode[] }[] = [
    { id: 'key-points', title: '핵심 포인트', items: summary.key_points?.map(point => <div key={point.id}>
      {row(point.point, point.ts)}
      {point.detail && <Line text={point.detail} small />}
      {quote(point.quote, point.ts)}
    </div>) ?? [] },
    { id: 'positions', title: '포지션', items: summary.positions?.map((position, i) => <div key={i}>
      <div className="flex min-w-0 items-center gap-2">
        <span className={`shrink-0 rounded px-1.5 py-0.5 text-xs ${actions[position.action][1]}`}>{actions[position.action][0]}</span>
        <div className="min-w-0 flex-1"><Line text={position.asset} /></div>{time(position.ts)}
      </div>
      {position.speaker && <Line text={position.speaker} small />}
      {position.when && <Line text={timings[position.when] ?? position.when} small />}
      {position.condition && <Line text={`조건: ${position.condition}`} small />}
      {position.detail && <Line text={position.detail} small />}
      {quote(position.quote, position.ts)}
    </div>) ?? [] },
    { id: 'scenarios', title: '시나리오', items: summary.scenarios?.map(item => row(`${item.if} → ${item.then}`, item.ts)) ?? [] },
    { id: 'numbers', title: '통계·숫자', items: summary.numbers?.map(item => row(item.fact, item.ts)) ?? [] },
    { id: 'terms', title: '용어', items: summary.terms?.map(item => row(`${item.term} — ${item.explain}${item.source ? ` · ${item.source}` : ''}`)) ?? [] },
    { id: 'takeaways', title: '학습 포인트', items: summary.takeaways?.map(item => row(`${takeawayTypes[item.type]} · ${item.text}`, item.ts)) ?? [] },
    { id: 'chapters', title: '챕터', items: summary.chapters?.map(item => row(item.title, item.ts)) ?? [] },
    { id: 'entities', title: '주요 대상', items: summary.entities?.map(item => row(item)) ?? [] },
    { id: 'open-questions', title: '열린 질문', items: summary.open_questions?.map(item => row(item)) ?? [] },
  ].filter(section => section.items.length > 0)

  return <div className="summary-body min-w-0">
    <section id="overview" aria-labelledby="overview-heading" className="mb-7 scroll-mt-24 border-l-4 border-[var(--accent)] pl-4">
      <h2 id="overview-heading" className="mb-3 text-lg font-semibold tracking-tight text-[var(--accent)]">핵심 요약</h2>
      <Line text={summary.tldr} />
      {summary.watch_guide && <>
        <span className="my-2 inline-block rounded border border-zinc-700 px-2 py-1 text-xs text-sky-300">{verdicts[summary.watch_guide.verdict]}</span>
        <Line text={summary.watch_guide.why} small />
      </>}
      <p className="mt-2 text-xs text-zinc-400">{contentTypes[summary.content_type] ?? summary.content_type}</p>
    </section>
    {sections.length > 0 && <>
      <ReaderNav sections={[{ id: 'overview', title: '핵심 요약' }, ...sections.map(({ id, title }) => ({ id, title }))]} />
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

import type { ReactNode } from 'react'
import { splitSentences } from './text'

export function SentenceList({ text }: { text: string }) {
  return <ul className="reader-sentences space-y-2 text-sm text-zinc-300">
    {splitSentences(text).map((sentence, i) => <li key={i} className="flex gap-2">
      <span aria-hidden="true" className="shrink-0 text-zinc-400">·</span>
      <span className="min-w-0">{sentence}</span>
    </li>)}
  </ul>
}

export function LimitedList({ items, label, bullets = false, compact = false }: { items: ReactNode[]; label: string; bullets?: boolean; compact?: boolean }) {
  const list = (children: ReactNode[]) => <ul className={compact ? 'flex flex-wrap gap-2' : bullets ? 'space-y-3' : 'divide-y divide-zinc-800/80'}>
    {children.map((item, i) => <li key={i} className={compact ? 'min-w-0 max-w-full' : bullets ? 'flex gap-3 text-sm' : 'py-4 first:pt-2'}>
      {bullets && <span aria-hidden="true" className="mt-2.5 h-1 w-1 shrink-0 rounded-full bg-sky-300" />}
      <div className="min-w-0 flex-1">{item}</div>
    </li>)}
  </ul>
  return <>
    {list(items.slice(0, 5))}
    {items.length > 5 && <details className="reader-more mt-2">
      <summary className="flex min-h-11 cursor-pointer items-center gap-2 text-sm font-medium text-sky-300">
        <span className="more-closed">{items.length - 5}개 더 보기<span className="sr-only"> · {label}</span></span>
        <span className="more-open">접기<span className="sr-only"> · {label}</span></span>
        <span aria-hidden="true" className="disclosure-arrow ml-auto">⌄</span>
      </summary>
      {list(items.slice(5))}
    </details>}
  </>
}

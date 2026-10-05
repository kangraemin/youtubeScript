import type { Quote } from '@/lib/supabase'
import { youtubeJumpUrl } from '@/lib/timestamp'
import { SentenceList } from './reader/ReaderPrimitives'

// 원문은 HTML에 남겨 검색·보조기술에서도 펼쳐 읽을 수 있게 한다.
export function QuoteList({ vid, quotes }: { vid: string; quotes?: Quote[] }) {
  if (!quotes?.length) return null
  return <details className="reader-quotes">
    <summary className="flex min-h-11 cursor-pointer items-center gap-2 text-xs text-zinc-400 hover:text-zinc-200">
      <span aria-hidden="true" className="disclosure-arrow">⌄</span>
      근거 발언 {quotes.length}개
    </summary>
    <ul className="space-y-4 rounded-lg bg-zinc-900/70 p-3 sm:p-4">
      {quotes.map((quote, i) => <li key={i}>
        <a href={youtubeJumpUrl(vid, quote.timestamp)} target="_blank" rel="noreferrer"
          aria-label={`${quote.timestamp}부터 YouTube에서 재생`}
          className="inline-flex min-h-11 min-w-11 items-center font-mono text-xs text-sky-300 hover:underline">
          {quote.timestamp}<span aria-hidden="true" className="ml-2">↗</span>
        </a>
        <SentenceList text={quote.text} />
      </li>)}
    </ul>
  </details>
}

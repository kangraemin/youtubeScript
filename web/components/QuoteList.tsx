import type { Quote } from '@/lib/supabase'
import { youtubeJumpUrl } from '@/lib/timestamp'
import { SentenceList } from './reader/ReaderPrimitives'

export function QuoteList({ vid, quotes }: { vid: string; quotes?: Quote[] }) {
  if (!quotes?.length) return null
  return (
    <details className="reader-quotes">
      <summary>
        <span className="quote-symbol" aria-hidden="true">
          “
        </span>
        실제로 한 말 <span className="quote-count">{quotes.length}</span>
        <span aria-hidden="true" className="disclosure-arrow">
          ⌄
        </span>
      </summary>
      <ul className="quote-content">
        {quotes.map((quote, i) => (
          <li key={i}>
            <a
              href={youtubeJumpUrl(vid, quote.timestamp)}
              target="_blank"
              rel="noreferrer"
              aria-label={`${quote.timestamp}부터 YouTube에서 재생`}
              className="time-link"
            >
              {quote.timestamp}
              <span aria-hidden="true"> ↗</span>
            </a>
            <SentenceList text={quote.text} />
          </li>
        ))}
      </ul>
    </details>
  )
}

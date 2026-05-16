import { Quote } from '@/lib/supabase'
import { youtubeJumpUrl } from '@/lib/timestamp'

export function QuoteList({ vid, quotes }: { vid: string; quotes?: Quote[] }) {
  if (!quotes?.length) return null
  return (
    <ul className="mt-2 space-y-1.5 border-l-2 border-zinc-700 pl-3">
      {quotes.map((q, i) => (
        <li key={i} className="text-sm text-zinc-300">
          <a
            href={youtubeJumpUrl(vid, q.timestamp)}
            target="_blank"
            rel="noreferrer"
            className="font-mono text-xs text-sky-400 hover:underline mr-2 bg-sky-400/10 px-1.5 py-0.5 rounded"
          >
            [{q.timestamp}]
          </a>
          <span className="italic text-zinc-400">&ldquo;{q.text}&rdquo;</span>
        </li>
      ))}
    </ul>
  )
}

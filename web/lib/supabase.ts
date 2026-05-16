import { createClient } from '@supabase/supabase-js'

export const supabase = createClient(
  process.env.NEXT_PUBLIC_SUPABASE_URL!,
  process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!
)

export type Quote = {
  timestamp: string  // "H:MM:SS"
  text: string
}

export type BuySell = {
  ticker: string
  reason: string
  speaker: string | null
  quotes: Quote[]
}

export type WatchItem = {
  topic: string
  reason: string
  speaker: string | null
  quotes: Quote[]
}

export type Term = {
  term: string
  explain: string
  context?: string
  source?: '영상' | '보충' | '영상+보충'
  quotes?: Quote[]
}

export type Summary = {
  buys?: BuySell[]
  sells?: BuySell[]
  watchlist?: WatchItem[]
  terms?: Term[]
  headline?: string
  raw_summary?: string
}

export type Transcript = {
  vid: string
  channel: string
  channel_slug: string
  title: string
  published_at: string | null
  transcript: string | null
  url: string
  summary: Summary | null
  summarized_at: string | null
}

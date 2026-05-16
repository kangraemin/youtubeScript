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

export type MacroView = {
  topic: string
  view: string
  speaker: string | null
  quotes: Quote[]
}

export type ChartLevel = {
  ticker: string
  level: string
  reason: string
  speaker: string | null
  quotes: Quote[]
}

export type Verdict = {
  condition: string
  consequence: string
  speaker: string | null
  quotes: Quote[]
}

export type Lesson = {
  type: 'rule' | 'counter' | 'reference' | 'analogy'
  lesson: string
  speaker: string | null
  quotes: Quote[]
}

export type DataPoint = {
  datum: string
  quotes: Quote[]
}

export type ActionItem = {
  action: string
  speaker: string | null
  quotes: Quote[]
}

export type Summary = {
  buys?: BuySell[]
  sells?: BuySell[]
  watchlist?: WatchItem[]
  terms?: Term[]
  macro_views?: MacroView[]
  chart_levels?: ChartLevel[]
  verdicts?: Verdict[]
  narrative?: string
  lessons?: Lesson[]
  data_points?: DataPoint[]
  action_items?: ActionItem[]
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

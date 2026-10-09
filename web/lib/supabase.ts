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

export type SummaryV2 = {
  schema?: never
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

export type SummaryV3 = {
  schema: 'v3'
  content_type: string
  tldr: string
  watch_guide: { verdict: 'skip' | 'skim' | 'watch'; why: string }
  key_points?: { id: string; point: string; detail?: string; ts?: string; quote?: string }[]
  positions?: {
    asset: string
    action: 'buy' | 'sell' | 'add' | 'reduce' | 'hold' | 'plan_buy' | 'plan_sell'
    when?: string
    condition?: string
    detail?: string
    speaker?: string | null
    ts?: string
    quote: string
  }[]
  scenarios?: { if: string; then: string; ts?: string }[]
  numbers?: { fact: string; ts?: string }[]
  terms?: Term[]
  takeaways?: { type: 'rule' | 'counter' | 'reference' | 'analogy'; text: string; ts?: string }[]
  chapters?: { ts: string; title: string }[]
  entities?: string[]
  open_questions?: string[]
}

export type Summary = SummaryV2 | SummaryV3

export type Transcript = {
  vid: string
  channel: string
  channel_slug: string
  title: string
  published_at: string | null
  transcript?: string | null
  url?: string
  summary?: Summary | null
  summarized_at: string | null
  // 영상 길이(초). 쇼츠 필터에 쓴다. -1은 삭제·비공개로 조회 불가, null은 아직 백필 전.
  duration_sec?: number | null
  // 브라우즈 피드 경량 RPC(feed_summaries) 전용 필드 — summary 전체 대신 headline+개수만.
  headline?: string | null
  n_buys?: number
  n_sells?: number
  n_watch?: number
  n_terms?: number
}

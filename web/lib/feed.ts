import { supabase, type Transcript } from './supabase'
import { cardPoints } from './cardPoints'

// 카드에는 개수 대신 실제 논점을 보낸다. 전체 요약 JSON은 서버에서만 읽고 카드 3개 요점만 전달한다.
export async function fetchFeedPage({
  channel = null,
  limit = 20,
  offset = 0,
  minDuration = 0,
}: {
  channel?: string | null
  limit?: number
  offset?: number
  minDuration?: number
} = {}) {
  const { data, error } = await supabase.rpc('feed_summaries', {
    p_channel: channel,
    p_limit: limit,
    p_offset: offset,
    p_min_duration: minDuration,
  })
  if (error) throw error
  const rows = (data ?? []) as Transcript[]
  if (!rows.length) return rows
  const content = await supabase
    .from('transcripts')
    .select('vid,summary')
    .in(
      'vid',
      rows.map((t) => t.vid),
    )
  if (content.error) throw content.error
  const summaries = new Map((content.data ?? []).map((t) => [t.vid, t.summary]))
  return rows.map((t) => ({
    ...t,
    preview_points: cardPoints({ ...t, summary: summaries.get(t.vid) }),
  }))
}

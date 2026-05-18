import type { Transcript } from '@/lib/supabase'

export type MatchPart = { text: string; hl: boolean }
export type MatchReason = { label: string; parts: MatchPart[] }

// 우선순위대로 검색어가 등장하는 필드를 찾아 최대 2개의 매칭근거 반환.
export function getMatchReasons(t: Transcript, qRaw: string): MatchReason[] {
  const q = qRaw.trim()
  if (!q) return []
  const ql = q.toLowerCase()
  const s = t.summary
  const candidates: { label: string; text: string }[] = []
  if (t.title) candidates.push({ label: '제목 일치', text: t.title })
  if (s?.headline) candidates.push({ label: '헤드라인', text: s.headline })
  for (const b of s?.buys ?? []) candidates.push({ label: '매수 코멘트', text: `${b.ticker} — ${b.reason}` })
  for (const b of s?.sells ?? []) candidates.push({ label: '매도 코멘트', text: `${b.ticker} — ${b.reason}` })
  for (const w of s?.watchlist ?? []) candidates.push({ label: '관전 포인트', text: `${w.topic} — ${w.reason}` })
  for (const tm of s?.terms ?? []) candidates.push({ label: '용어 설명', text: `${tm.term} — ${tm.explain}` })
  if (s?.narrative) candidates.push({ label: '내러티브', text: s.narrative })
  if (s?.raw_summary) candidates.push({ label: '요약', text: s.raw_summary })

  const out: MatchReason[] = []
  for (const c of candidates) {
    const idx = c.text.toLowerCase().indexOf(ql)
    if (idx === -1) continue
    const start = Math.max(0, idx - 40)
    const end = Math.min(c.text.length, idx + q.length + 60)
    const pre = (start > 0 ? '…' : '') + c.text.slice(start, idx)
    const mid = c.text.slice(idx, idx + q.length)
    const post = c.text.slice(idx + q.length, end) + (end < c.text.length ? '…' : '')
    out.push({
      label: c.label,
      parts: [
        { text: pre, hl: false },
        { text: mid, hl: true },
        { text: post, hl: false },
      ],
    })
    if (out.length >= 2) break
  }
  return out
}

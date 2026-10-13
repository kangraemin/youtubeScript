import type { Summary, Transcript } from './supabase'
import { splitHeadline } from '@/components/reader/text'
export type CardPoint = { title: string; text: string }
export function cardPoints(t: Transcript): CardPoint[] {
  if (t.preview_points?.length) return t.preview_points
  const s = t.summary
  const points: CardPoint[] = []
  if (s?.reading_guide) {
    const g = s.reading_guide
    return [
      { title: '다룬 이야기', text: g.title },
      ...g.perspectives
        .slice(0, 2)
        .map((p) => ({ title: `${p.name}의 관점`, text: p.view })),
    ]
  }
  if (s?.schema === 'v3') {
    for (const p of s.key_points ?? [])
      points.push({
        title: p.point,
        text: p.detail ? p.detail : '',
      })
    if (!points.length) points.push({ title: '요점', text: s.tldr })
  } else if (s) {
    for (const p of s.buys ?? [])
      points.push({ title: `${p.ticker} · 매수`, text: p.reason })
    for (const p of s.sells ?? [])
      points.push({ title: `${p.ticker} · 매도`, text: p.reason })
    for (const p of s.verdicts ?? [])
      points.push({ title: p.condition, text: p.consequence })
    for (const p of s.macro_views ?? [])
      points.push({ title: p.topic, text: p.view })
    for (const p of s.watchlist ?? [])
      points.push({ title: p.topic, text: p.reason })
    if (!points.length)
      for (const p of s.terms ?? [])
        points.push({ title: p.term, text: p.explain })
  }
  if (!points.length)
    for (const p of splitHeadline(
      (s as Summary & { headline?: string })?.headline ?? t.headline ?? '',
    ))
      points.push({ title: '', text: p })
  return points.slice(0, 3)
}

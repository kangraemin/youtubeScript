import Link from 'next/link'
import { Transcript } from '@/lib/supabase'
import { getChannelMeta } from '@/lib/channels'
import { thumbnailUrl } from '@/lib/youtube'
import { getMatchReasons } from '@/lib/matchReason'

type Props = {
  t: Transcript
  showChannel?: boolean
  searchQuery?: string
}

export function VideoCard({ t, showChannel = true, searchQuery }: Props) {
  const ch = getChannelMeta(t.channel_slug, t.channel)
  const s = t.summary
  // 검색의 전체 요약과 브라우즈의 경량 응답을 모두 표시해야 한다.
  const headline = (s?.schema === 'v3' ? s.tldr : s?.headline) ?? t.headline ?? null
  const hasMeta = !!s || headline != null || t.n_buys != null
  const reasons = searchQuery ? getMatchReasons(t, searchQuery) : []

  return (
    <Link
      href={`/video/${t.vid}`}
      className="group flex min-w-0 gap-3 rounded-xl border border-zinc-800/80 bg-zinc-900/30 p-3 transition-colors hover:border-zinc-600 hover:bg-zinc-900/70 sm:block sm:p-0 sm:overflow-hidden"
    >
      <div className="relative aspect-video w-24 shrink-0 self-start overflow-hidden rounded-md bg-zinc-900 sm:w-full sm:rounded-none">
        {/* eslint-disable-next-line @next/next/no-img-element */}
        <img src={thumbnailUrl(t.vid, 'mq')} alt="" loading="lazy" className="h-full w-full object-cover" />
      </div>
      <div className="min-w-0 flex-1 sm:p-4">
        <h3 className="text-sm font-semibold leading-relaxed line-clamp-2 mb-1.5 text-zinc-100">
          {t.title}
        </h3>
        {headline ? (
          <p className="text-sm text-zinc-400 line-clamp-1 mb-2 leading-relaxed">{headline}</p>
        ) : (
          <p className="text-sm text-zinc-400 mb-2">{hasMeta ? '요약 읽기' : '요약 대기 중'}</p>
        )}
        {reasons.length > 0 && (
          <div className="mt-1 mb-2 space-y-1">
            {reasons.map((r, i) => (
              <div key={i} className="text-xs leading-relaxed line-clamp-2">
                <span className="inline-block px-1 py-0.5 rounded bg-zinc-800 text-zinc-400 mr-1 align-middle">
                  {r.label}
                </span>
                <span className="text-zinc-400">
                  {r.parts.map((p, j) =>
                    p.hl ? (
                      <mark key={j} className="bg-[var(--accent)] text-zinc-950 rounded px-0.5">
                        {p.text}
                      </mark>
                    ) : (
                      <span key={j}>{p.text}</span>
                    )
                  )}
                </span>
              </div>
            ))}
          </div>
        )}
        <div className="flex flex-wrap gap-1 empty:hidden mb-2" aria-label="포지션 태그">
          <CountChip label="매수" count={(s?.schema === 'v3' ? s.positions?.filter(p => ['buy', 'add', 'plan_buy'].includes(p.action)).length : s?.buys?.length) ?? t.n_buys} tone="buy" />
          <CountChip label="매도" count={(s?.schema === 'v3' ? s.positions?.filter(p => ['sell', 'reduce', 'plan_sell'].includes(p.action)).length : s?.sells?.length) ?? t.n_sells} tone="sell" />
          <CountChip label="관전" count={(s?.schema === 'v3' ? s.scenarios?.length : s?.watchlist?.length) ?? t.n_watch} />
          <CountChip label="용어" count={s?.terms?.length ?? t.n_terms} />
        </div>
        <div className="flex flex-wrap items-center gap-x-2 gap-y-1 text-xs text-zinc-400">
          {showChannel && <span>{ch.name}</span>}
          {t.published_at && <time dateTime={t.published_at}>{t.published_at.slice(0, 10)}</time>}
        </div>
      </div>
    </Link>
  )
}

function CountChip({ label, count, tone }: { label: string; count?: number | null; tone?: 'buy' | 'sell' }) {
  if (!count || count < 0) return null
  const color = tone === 'buy' ? 'bg-emerald-950 text-emerald-300'
    : tone === 'sell' ? 'bg-rose-950 text-rose-300' : 'bg-zinc-800 text-zinc-300'
  return <span className={`whitespace-nowrap rounded px-1 py-0.5 text-xs tabular-nums ${color}`}>{label} {count}</span>
}

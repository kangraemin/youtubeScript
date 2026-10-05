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

function CountChip({ label, count, tone }: { label: string; count: number; tone: string }) {
  if (!count) return null
  return (
    <span className={`px-1.5 py-0.5 rounded text-xs font-medium ${tone}`}>
      {label} {count}
    </span>
  )
}

export function VideoCard({ t, showChannel = true, searchQuery }: Props) {
  const ch = getChannelMeta(t.channel_slug, t.channel)
  const s = t.summary
  // 카운트·헤드라인을 full summary(검색) 또는 경량 RPC 필드(브라우즈) 양쪽에서 읽음.
  const headline = s?.headline ?? t.headline ?? null
  const buys = s?.buys?.length ?? t.n_buys ?? 0
  const sells = s?.sells?.length ?? t.n_sells ?? 0
  const watch = s?.watchlist?.length ?? t.n_watch ?? 0
  const terms = s?.terms?.length ?? t.n_terms ?? 0
  const hasMeta = !!s || headline != null || t.n_buys != null
  const reasons = searchQuery ? getMatchReasons(t, searchQuery) : []

  return (
    <Link
      href={`/video/${t.vid}`}
      className="group flex sm:block rounded-xl overflow-hidden border border-zinc-800 hover:border-zinc-600 bg-zinc-900/40 transition-all hover:-translate-y-0.5"
      style={{ borderTopColor: ch.hex, borderTopWidth: 3 }}
    >
      {/* 모바일은 좌측 작은 썸네일 리스트형 — 전폭 16:9였을 땐 한 화면에 카드 2.3장(2026-10-05 실측) */}
      <div className="relative w-32 shrink-0 self-start aspect-video bg-zinc-900 overflow-hidden sm:w-auto">
        {/* eslint-disable-next-line @next/next/no-img-element */}
        <img
          src={thumbnailUrl(t.vid, 'mq')}
          alt={t.title}
          loading="lazy"
          className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-300"
        />
        {showChannel && (
          <div
            className="absolute top-1 left-1 sm:top-2 sm:left-2 px-1.5 sm:px-2 py-0.5 rounded-md text-[11px] sm:text-xs font-semibold backdrop-blur-sm"
            style={{ background: `${ch.hex}cc`, color: '#0a0a0a' }}
          >
            {ch.name}
          </div>
        )}
      </div>
      <div className="min-w-0 flex-1 p-3">
        <h3 className="text-sm font-semibold leading-snug line-clamp-2 mb-1.5 text-zinc-100">
          {t.title}
        </h3>
        {headline ? (
          <p className="text-sm text-zinc-300 line-clamp-2 mb-2 leading-relaxed">{headline}</p>
        ) : (
          <p className="text-sm text-zinc-400 mb-2">(요약 대기 중)</p>
        )}
        {hasMeta && (
          <div className="flex flex-wrap gap-1 mb-2">
            <CountChip label="매수" count={buys} tone="bg-emerald-500/15 text-emerald-300" />
            <CountChip label="매도" count={sells} tone="bg-rose-500/15 text-rose-300" />
            <CountChip label="관전" count={watch} tone="bg-amber-500/15 text-amber-300" />
            <CountChip label="용어" count={terms} tone="bg-violet-500/15 text-violet-300" />
          </div>
        )}
        {reasons.length > 0 && (
          <div className="mt-1 mb-2 space-y-1">
            {reasons.map((r, i) => (
              <div key={i} className="text-xs leading-relaxed">
                <span className="inline-block px-1 py-0.5 rounded bg-zinc-800 text-zinc-400 mr-1 align-middle">
                  {r.label}
                </span>
                <span className="text-zinc-400">
                  {r.parts.map((p, j) =>
                    p.hl ? (
                      <mark key={j} className="bg-amber-400/80 text-zinc-950 rounded px-0.5">
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
        <div className="text-xs text-zinc-400">{t.published_at}</div>
      </div>
    </Link>
  )
}

import Link from 'next/link'
import { Transcript } from '@/lib/supabase'
import { getChannelMeta } from '@/lib/channels'
import { thumbnailUrl } from '@/lib/youtube'

type Props = {
  t: Transcript
  showChannel?: boolean
}

function CountChip({ label, count, tone }: { label: string; count: number; tone: string }) {
  if (!count) return null
  return (
    <span className={`px-1.5 py-0.5 rounded text-[10px] font-medium ${tone}`}>
      {label} {count}
    </span>
  )
}

export function VideoCard({ t, showChannel = true }: Props) {
  const ch = getChannelMeta(t.channel_slug, t.channel)
  const s = t.summary
  const buys = s?.buys?.length ?? 0
  const sells = s?.sells?.length ?? 0
  const watch = s?.watchlist?.length ?? 0
  const terms = s?.terms?.length ?? 0

  return (
    <Link
      href={`/video/${t.vid}`}
      className="group block rounded-xl overflow-hidden border border-zinc-800 hover:border-zinc-600 bg-zinc-900/40 transition-all hover:-translate-y-0.5"
      style={{ borderTopColor: ch.hex, borderTopWidth: 3 }}
    >
      <div className="relative aspect-video bg-zinc-900 overflow-hidden">
        {/* eslint-disable-next-line @next/next/no-img-element */}
        <img
          src={thumbnailUrl(t.vid, 'mq')}
          alt={t.title}
          loading="lazy"
          className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-300"
        />
        {showChannel && (
          <div
            className="absolute top-2 left-2 px-2 py-0.5 rounded-md text-[10px] font-semibold backdrop-blur-sm"
            style={{ background: `${ch.hex}cc`, color: '#0a0a0a' }}
          >
            {ch.name}
          </div>
        )}
      </div>
      <div className="p-3">
        <h3 className="text-sm font-semibold leading-snug line-clamp-2 mb-1.5 text-zinc-100">
          {t.title}
        </h3>
        {s?.headline ? (
          <p className="text-xs text-zinc-400 line-clamp-2 mb-2 leading-relaxed">{s.headline}</p>
        ) : (
          <p className="text-xs text-zinc-600 mb-2">(요약 대기 중)</p>
        )}
        {s && (
          <div className="flex flex-wrap gap-1 mb-2">
            <CountChip label="매수" count={buys} tone="bg-emerald-500/15 text-emerald-300" />
            <CountChip label="매도" count={sells} tone="bg-rose-500/15 text-rose-300" />
            <CountChip label="관전" count={watch} tone="bg-amber-500/15 text-amber-300" />
            <CountChip label="용어" count={terms} tone="bg-violet-500/15 text-violet-300" />
          </div>
        )}
        <div className="text-[10px] text-zinc-600">{t.published_at}</div>
      </div>
    </Link>
  )
}

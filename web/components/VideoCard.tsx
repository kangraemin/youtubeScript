import Link from 'next/link'
import { Transcript } from '@/lib/supabase'
import { getChannelMeta } from '@/lib/channels'
import { thumbnailUrl } from '@/lib/youtube'
import { getMatchReasons } from '@/lib/matchReason'

type Props = { t: Transcript; showChannel?: boolean; searchQuery?: string }
export function VideoCard({ t, showChannel = true, searchQuery }: Props) {
  const ch = getChannelMeta(t.channel_slug, t.channel),
    s = t.summary
  const headline =
    (s?.schema === 'v3' ? s.tldr : s?.headline) ?? t.headline ?? null
  const reasons = searchQuery ? getMatchReasons(t, searchQuery) : []
  const duration =
    t.duration_sec && t.duration_sec > 0
      ? `${Math.floor(t.duration_sec / 60)}분`
      : null
  return (
    <Link href={`/video/${t.vid}`} className="video-card">
      <div className="video-meta">
        {showChannel && (
          <span className="channel-name">
            <span className="channel-avatar" aria-hidden="true">
              {ch.name.slice(0, 1)}
            </span>
            {ch.name}
          </span>
        )}
        {t.published_at && (
          <time dateTime={t.published_at}>
            {t.published_at.slice(5, 10).replace('-', '.')}
          </time>
        )}
      </div>
      <div className="video-card-main">
        <div className="video-copy">
          <h3>{t.title}</h3>
          {headline ? (
            <p className="video-excerpt">{headline}</p>
          ) : (
            <p className="video-excerpt">요약을 준비하고 있어요.</p>
          )}
        </div>
        <div className="video-thumb">
          <img src={thumbnailUrl(t.vid, 'mq')} alt="" loading="lazy" />
          {duration && <span>{duration}</span>}
        </div>
      </div>
      {reasons.length > 0 && (
        <div className="search-matches">
          {reasons.map((r, i) => (
            <p key={i}>
              <span>{r.label}</span>
              {r.parts.map((p, j) =>
                p.hl ? (
                  <mark key={j}>{p.text}</mark>
                ) : (
                  <span key={j}>{p.text}</span>
                ),
              )}
            </p>
          ))}
        </div>
      )}
      <div className="video-card-bottom">
        <div className="video-signals" aria-label="요약에 담긴 내용">
          <CountChip
            label="매수"
            count={
              (s?.schema === 'v3'
                ? s.positions?.filter((p) =>
                    ['buy', 'add', 'plan_buy'].includes(p.action),
                  ).length
                : s?.buys?.length) ?? t.n_buys
            }
            tone="buy"
          />
          <CountChip
            label="매도"
            count={
              (s?.schema === 'v3'
                ? s.positions?.filter((p) =>
                    ['sell', 'reduce', 'plan_sell'].includes(p.action),
                  ).length
                : s?.sells?.length) ?? t.n_sells
            }
            tone="sell"
          />
          <CountChip
            label="관전"
            count={
              (s?.schema === 'v3'
                ? s.scenarios?.length
                : s?.watchlist?.length) ?? t.n_watch
            }
          />
          <CountChip label="경제 용어" count={s?.terms?.length ?? t.n_terms} />
        </div>
        <span className="read-link">
          읽기 <span aria-hidden="true">↗</span>
        </span>
      </div>
    </Link>
  )
}
function CountChip({
  label,
  count,
  tone,
}: {
  label: string
  count?: number | null
  tone?: 'buy' | 'sell'
}) {
  if (!count || count < 0) return null
  return (
    <span className={`signal signal-${tone ?? 'neutral'}`}>
      {label} <b>{count}</b>
    </span>
  )
}

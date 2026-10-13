import Link from 'next/link'
import { getReadingGuide } from '@/lib/readingGuides'
import { supabase, Transcript } from '@/lib/supabase'
import { SummaryCard } from '@/components/SummaryCard'
import { getChannelMeta } from '@/lib/channels'
import { watchUrl } from '@/lib/youtube'

export const revalidate = 3600 // 상세 콘텐츠는 요약 후 거의 불변 — 반복 방문 캐시 적중(60s마다 재생성 방지)

export default async function VideoPage({
  params,
}: {
  params: Promise<{ vid: string }>
}) {
  const { vid } = await params
  const { data } = await supabase
    .from('transcripts')
    .select(
      'vid,channel,channel_slug,title,published_at,url,summary,summarized_at',
    )
    .eq('vid', vid)
    .single()

  const t = data as Transcript | null
  if (!t) {
    return (
      <main className="reader-shell">
        <Link href="/" className="back-link">
          ← 홈
        </Link>
        <p className="text-zinc-400 mt-4">영상을 찾을 수 없어요.</p>
      </main>
    )
  }

  const ch = getChannelMeta(t.channel_slug, t.channel)

  return (
    <main className="reader-shell">
      <Link href={`/channel/${t.channel_slug}`} className="back-link">
        ← {ch.name}
      </Link>

      <article className="mt-5">
        <header className="video-heading">
          <p className="eyebrow">영상 요약</p>
          <h1 className="detail-title">{t.title}</h1>
          <div className="detail-meta">
            <span className="detail-channel">{ch.name}</span>
            {t.published_at && (
              <time dateTime={t.published_at}>
                {t.published_at.slice(0, 10)}
              </time>
            )}
            {t.summarized_at && (
              <span>{t.summarized_at.slice(0, 10)} 요약</span>
            )}
            <a
              href={t.url || watchUrl(t.vid)}
              target="_blank"
              rel="noreferrer"
              className="original-link"
            >
              YouTube 원본 보기{' '}
              <span aria-hidden="true" className="ml-1">
                ↗
              </span>
            </a>
          </div>
        </header>
      </article>

      <div className="detail-summary">
        <SummaryCard
          vid={t.vid}
          summary={
            t.summary
              ? {
                  ...t.summary,
                  reading_guide:
                    getReadingGuide(t.vid) ?? t.summary.reading_guide,
                }
              : null
          }
          channel={t.channel}
        />
      </div>
    </main>
  )
}

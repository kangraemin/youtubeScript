import Link from 'next/link'
import { supabase, Transcript } from '@/lib/supabase'
import { SummaryCard } from '@/components/SummaryCard'
import { getChannelMeta } from '@/lib/channels'
import { thumbnailUrl, watchUrl } from '@/lib/youtube'

export const revalidate = 3600 // 상세 콘텐츠는 요약 후 거의 불변 — 반복 방문 캐시 적중(60s마다 재생성 방지)

export default async function VideoPage({
  params,
}: {
  params: Promise<{ vid: string }>
}) {
  const { vid } = await params
  const { data } = await supabase
    .from('transcripts')
    .select('vid,channel,channel_slug,title,published_at,url,summary,summarized_at')
    .eq('vid', vid)
    .single()

  const t = data as Transcript | null
  if (!t) {
    return (
      <main className="max-w-3xl mx-auto px-5 py-8">
        <Link href="/" className="text-sm text-zinc-400 hover:text-zinc-200">
          ← 홈
        </Link>
        <p className="text-zinc-500 mt-4">영상을 찾을 수 없어요.</p>
      </main>
    )
  }

  const ch = getChannelMeta(t.channel_slug, t.channel)
  const s = t.summary

  return (
    <main className="max-w-4xl mx-auto px-4 sm:px-6 py-8">
      <Link href={`/channel/${t.channel_slug}`} className="text-sm text-zinc-400 hover:text-zinc-200">
        ← {ch.name}
      </Link>

      {/* 큰 hq 썸네일이 PC 첫 화면의 절반을 차지해 요약이 아래로 밀렸다 → 작은 썸네일 + 링크 한 줄로 */}
      <article className="mt-4">
        <header>
          <div className="flex items-center gap-2 mb-3 text-xs">
            <span
              className="px-2 py-0.5 rounded-md font-semibold"
              style={{ background: `${ch.hex}cc`, color: '#0a0a0a' }}
            >
              {ch.name}
            </span>
            <span className="text-zinc-400">{t.published_at}</span>
            {t.summarized_at && (
              <span className="text-zinc-400">· {t.summarized_at.slice(0, 10)} 요약</span>
            )}
          </div>
          <h1 className="text-2xl sm:text-3xl font-bold leading-tight tracking-tight">{t.title}</h1>
          {s?.headline && (
            <p className="mt-3 text-base text-zinc-300 leading-relaxed">{s.headline}</p>
          )}
        </header>

        <a
          href={t.url || watchUrl(t.vid)}
          target="_blank"
          rel="noreferrer"
          className="mt-4 flex items-center gap-3 rounded-lg border border-zinc-800 bg-zinc-900/50 p-2 pr-4 hover:border-zinc-600"
        >
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img
            src={thumbnailUrl(t.vid, 'mq')}
            alt=""
            className="w-28 aspect-video rounded object-cover shrink-0"
          />
          <span className="text-sm font-semibold text-zinc-200">▶ YouTube에서 원본 보기</span>
        </a>
      </article>

      <div className="mt-8">
        <SummaryCard vid={t.vid} summary={t.summary ?? null} />
      </div>
    </main>
  )
}

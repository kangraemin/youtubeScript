import Link from 'next/link'
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
    .select('vid,channel,channel_slug,title,published_at,url,summary,summarized_at')
    .eq('vid', vid)
    .single()

  const t = data as Transcript | null
  if (!t) {
    return (
      <main className="max-w-3xl mx-auto px-5 py-8">
        <Link href="/" className="inline-flex min-h-11 min-w-11 items-center text-sm text-zinc-400 hover:text-zinc-200">
          ← 홈
        </Link>
        <p className="text-zinc-400 mt-4">영상을 찾을 수 없어요.</p>
      </main>
    )
  }

  const ch = getChannelMeta(t.channel_slug, t.channel)

  return (
    <main className="max-w-3xl mx-auto px-4 sm:px-6 py-6 sm:py-10">
      <Link href={`/channel/${t.channel_slug}`} className="inline-flex min-h-11 min-w-11 items-center text-sm text-zinc-400 hover:text-zinc-200">
        ← {ch.name}
      </Link>

      <article className="mt-5">
        <header className="border-b border-zinc-800 pb-6">
          <p className="mb-3 text-xs font-medium tracking-widest text-zinc-400">영상 요약</p>
          <h1 className="text-2xl font-bold leading-snug tracking-tight sm:text-3xl">{t.title}</h1>
          <div className="mt-4 flex flex-wrap items-center gap-x-3 gap-y-1 text-xs text-zinc-400">
            <span className="font-medium text-zinc-200">{ch.name}</span>
            {t.published_at && <time dateTime={t.published_at}>{t.published_at.slice(0, 10)}</time>}
            {t.summarized_at && <span>{t.summarized_at.slice(0, 10)} 요약</span>}
            <a href={t.url || watchUrl(t.vid)} target="_blank" rel="noreferrer"
              className="inline-flex min-h-11 items-center text-sky-300 hover:underline sm:ml-auto">
              YouTube 원본 보기 <span aria-hidden="true" className="ml-1">↗</span>
            </a>
          </div>
        </header>
      </article>

      <div className="mt-8">
        <SummaryCard vid={t.vid} summary={t.summary ?? null} channel={t.channel} />
      </div>
    </main>
  )
}

import Link from 'next/link'
import { supabase, Transcript } from '@/lib/supabase'
import { SummaryCard } from '@/components/SummaryCard'
import { getChannelMeta } from '@/lib/channels'
import { thumbnailUrl, watchUrl } from '@/lib/youtube'

export const revalidate = 60

export default async function VideoPage({
  params,
}: {
  params: Promise<{ vid: string }>
}) {
  const { vid } = await params
  const { data } = await supabase
    .from('transcripts')
    .select('*')
    .eq('vid', vid)
    .single()

  const t = data as Transcript | null
  if (!t) {
    return (
      <main className="max-w-3xl mx-auto px-5 py-8">
        <Link href="/" className="text-xs text-zinc-500 hover:text-zinc-200">
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
      <Link href={`/channel/${t.channel_slug}`} className="text-xs text-zinc-500 hover:text-zinc-200">
        ← {ch.name}
      </Link>

      <article className="mt-4">
        <a
          href={t.url || watchUrl(t.vid)}
          target="_blank"
          rel="noreferrer"
          className="relative block aspect-video rounded-xl overflow-hidden bg-zinc-900 border border-zinc-800 hover:border-zinc-600 group"
          style={{ borderTopColor: ch.hex, borderTopWidth: 4 }}
        >
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img
            src={thumbnailUrl(t.vid, 'hq')}
            alt={t.title}
            className="w-full h-full object-cover group-hover:scale-[1.02] transition-transform duration-500"
          />
          <div className="absolute inset-0 flex items-center justify-center bg-black/0 group-hover:bg-black/30 transition-colors">
            <div className="opacity-0 group-hover:opacity-100 transition-opacity flex items-center gap-2 px-4 py-2 rounded-full bg-red-600 text-white text-sm font-semibold">
              ▶ YouTube에서 보기
            </div>
          </div>
        </a>

        <header className="mt-6">
          <div className="flex items-center gap-2 mb-3 text-xs">
            <span
              className="px-2 py-0.5 rounded-md font-semibold"
              style={{ background: `${ch.hex}cc`, color: '#0a0a0a' }}
            >
              {ch.name}
            </span>
            <span className="text-zinc-500">{t.published_at}</span>
            {t.summarized_at && (
              <span className="text-zinc-600">· {t.summarized_at.slice(0, 10)} 요약</span>
            )}
          </div>
          <h1 className="text-2xl sm:text-3xl font-bold leading-tight tracking-tight">{t.title}</h1>
          {s?.headline && (
            <p className="mt-3 text-base text-zinc-300 leading-relaxed">{s.headline}</p>
          )}
        </header>
      </article>

      <div className="mt-8">
        <SummaryCard vid={t.vid} summary={t.summary} />
      </div>

      {t.transcript && (
        <details className="mt-10 rounded-lg border border-zinc-800 bg-zinc-900/40 p-4">
          <summary className="cursor-pointer text-sm font-semibold text-zinc-400 hover:text-zinc-200">
            📄 원본 스크립트 보기
          </summary>
          <pre className="mt-3 p-3 bg-zinc-950/50 rounded text-xs text-zinc-400 leading-relaxed whitespace-pre-wrap font-mono">
            {t.transcript}
          </pre>
        </details>
      )}
    </main>
  )
}

import Link from 'next/link'
import { supabase, Transcript } from '@/lib/supabase'
import { getChannelMeta } from '@/lib/channels'
import { VideoCard } from '@/components/VideoCard'

export const revalidate = 60

export default async function ChannelPage({
  params,
  searchParams,
}: {
  params: Promise<{ slug: string }>
  searchParams: Promise<{ filter?: string }>
}) {
  const { slug } = await params
  const sp = await searchParams
  const filter = sp.filter ?? 'all' // all | summarized | pending

  let query = supabase
    .from('transcripts')
    .select('vid,channel,channel_slug,title,published_at,summary,summarized_at')
    .eq('channel_slug', slug)
    .order('published_at', { ascending: false, nullsFirst: false })
    .limit(200)

  if (filter === 'summarized') query = query.not('summary', 'is', null)
  if (filter === 'pending') query = query.is('summary', null)

  const { data } = await query
  const items = (data ?? []) as Transcript[]

  const ch = getChannelMeta(slug, items[0]?.channel ?? slug)
  const summarizedCount = items.filter((t) => t.summary).length

  const filterLink = (key: string, label: string) => (
    <Link
      href={`/channel/${slug}?filter=${key}`}
      className={`px-3 py-1 rounded-full text-xs font-medium transition-colors ${
        filter === key
          ? 'text-zinc-950'
          : 'text-zinc-400 hover:text-zinc-100 bg-zinc-900/60 hover:bg-zinc-800/60 border border-zinc-800'
      }`}
      style={filter === key ? { background: ch.hex } : undefined}
    >
      {label}
    </Link>
  )

  return (
    <main className="max-w-7xl mx-auto px-4 sm:px-6 py-8">
      <Link href="/" className="text-xs text-zinc-500 hover:text-zinc-200">
        ← 홈
      </Link>

      <header className="mt-3 mb-8 flex items-center justify-between gap-4 flex-wrap">
        <div>
          <h1
            className="text-3xl font-bold tracking-tight"
            style={{ color: ch.hex }}
          >
            {ch.name}
          </h1>
          <p className="text-sm text-zinc-500 mt-1">
            전체 {items.length}편 · 요약 {summarizedCount}편
          </p>
        </div>
        <div className="flex gap-2">
          {filterLink('all', '전체')}
          {filterLink('summarized', '요약')}
          {filterLink('pending', '대기')}
        </div>
      </header>

      {items.length === 0 ? (
        <div className="rounded-lg border border-zinc-800 bg-zinc-900/50 p-8 text-center text-zinc-500">
          이 채널엔 표시할 영상이 없어요.
        </div>
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
          {items.map((t) => (
            <VideoCard key={t.vid} t={t} showChannel={false} />
          ))}
        </div>
      )}
    </main>
  )
}

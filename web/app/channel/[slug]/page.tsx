import Link from 'next/link'
import { supabase } from '@/lib/supabase'
import { getChannelMeta } from '@/lib/channels'
import { InfiniteList } from '@/components/InfiniteList'

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
  const filter = (sp.filter ?? 'all') as 'all' | 'summarized' | 'pending'

  // 헤더의 채널명 노출용 + 필터 카운트
  const [headRes, allCountRes, summarizedCountRes] = await Promise.all([
    supabase.from('transcripts').select('channel').eq('channel_slug', slug).limit(1),
    supabase
      .from('transcripts')
      .select('vid', { count: 'exact', head: true })
      .eq('channel_slug', slug),
    supabase
      .from('transcripts')
      .select('vid', { count: 'exact', head: true })
      .eq('channel_slug', slug)
      .not('summary', 'is', null),
  ])
  const ch = getChannelMeta(slug, headRes.data?.[0]?.channel ?? slug)
  const totalAll = allCountRes.count ?? 0
  const totalSummarized = summarizedCountRes.count ?? 0
  const totalPending = Math.max(0, totalAll - totalSummarized)

  const mode =
    filter === 'summarized'
      ? 'channel-summarized'
      : filter === 'pending'
      ? 'channel-pending'
      : 'channel-all'

  const filterLink = (key: 'all' | 'summarized' | 'pending', label: string, n: number) => (
    <Link
      href={`/channel/${slug}${key === 'all' ? '' : `?filter=${key}`}`}
      className={`px-3 py-1 rounded-full text-xs font-medium transition-colors ${
        filter === key
          ? 'text-zinc-950'
          : 'text-zinc-400 hover:text-zinc-100 bg-zinc-900/60 hover:bg-zinc-800/60 border border-zinc-800'
      }`}
      style={filter === key ? { background: ch.hex } : undefined}
    >
      {label} {n}
    </Link>
  )

  return (
    <main className="max-w-7xl mx-auto px-4 sm:px-6 py-8">
      <Link href="/" className="text-xs text-zinc-500 hover:text-zinc-200">
        ← 홈
      </Link>

      <header className="mt-3 mb-8 flex items-center justify-between gap-4 flex-wrap">
        <div>
          <h1 className="text-3xl font-bold tracking-tight" style={{ color: ch.hex }}>
            {ch.name}
          </h1>
          <p className="text-sm text-zinc-500 mt-1">
            전체 {totalAll}편 · 요약 {totalSummarized}편
          </p>
        </div>
        <div className="flex gap-2">
          {filterLink('all', '전체', totalAll)}
          {filterLink('summarized', '요약', totalSummarized)}
          {filterLink('pending', '대기', totalPending)}
        </div>
      </header>

      <InfiniteList mode={mode} channelSlug={slug} showChannel={false} pageSize={20} />
    </main>
  )
}

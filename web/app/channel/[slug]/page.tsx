import Link from 'next/link'
import { supabase, Transcript } from '@/lib/supabase'
import { getChannelMeta } from '@/lib/channels'
import { VideoCard } from '@/components/VideoCard'
import { Pagination } from '@/components/Pagination'

export const revalidate = 60

const PAGE_SIZE = 48

export default async function ChannelPage({
  params,
  searchParams,
}: {
  params: Promise<{ slug: string }>
  searchParams: Promise<{ filter?: string; page?: string }>
}) {
  const { slug } = await params
  const sp = await searchParams
  const filter = sp.filter ?? 'all'
  const page = Math.max(1, parseInt(sp.page ?? '1', 10) || 1)
  const from = (page - 1) * PAGE_SIZE
  const to = from + PAGE_SIZE - 1

  let query = supabase
    .from('transcripts')
    .select('vid,channel,channel_slug,title,published_at,summary,summarized_at', {
      count: 'exact',
    })
    .eq('channel_slug', slug)
    .order('published_at', { ascending: false, nullsFirst: false })
    .range(from, to)

  if (filter === 'summarized') query = query.not('summary', 'is', null)
  if (filter === 'pending') query = query.is('summary', null)

  const { data, count } = await query
  const items = (data ?? []) as Transcript[]
  const total = count ?? items.length

  const ch = getChannelMeta(slug, items[0]?.channel ?? slug)

  // 필터별 카운트는 별도로 빠르게 가져온다 (head: true로 데이터 안 받음)
  const [allCountRes, summarizedCountRes] = await Promise.all([
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
  const totalAll = allCountRes.count ?? 0
  const totalSummarized = summarizedCountRes.count ?? 0
  const totalPending = Math.max(0, totalAll - totalSummarized)

  const filterLink = (key: string, label: string, n: number) => (
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

  const extraQuery: Record<string, string | undefined> = filter === 'all' ? {} : { filter }

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
            전체 {totalAll}편 · 요약 {totalSummarized}편 ·{' '}
            <span className="text-zinc-600">
              {page}/{Math.max(1, Math.ceil(total / PAGE_SIZE))} 페이지
            </span>
          </p>
        </div>
        <div className="flex gap-2">
          {filterLink('all', '전체', totalAll)}
          {filterLink('summarized', '요약', totalSummarized)}
          {filterLink('pending', '대기', totalPending)}
        </div>
      </header>

      {items.length === 0 ? (
        <div className="rounded-lg border border-zinc-800 bg-zinc-900/50 p-8 text-center text-zinc-500">
          표시할 영상이 없어요.
        </div>
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
          {items.map((t) => (
            <VideoCard key={t.vid} t={t} showChannel={false} />
          ))}
        </div>
      )}

      <Pagination
        basePath={`/channel/${slug}`}
        page={page}
        pageSize={PAGE_SIZE}
        total={total}
        extraQuery={extraQuery}
      />
    </main>
  )
}

import Link from 'next/link'
import { supabase, Transcript } from '@/lib/supabase'
import { VideoCard } from '@/components/VideoCard'
import { Pagination } from '@/components/Pagination'

export const revalidate = 60

const PAGE_SIZE = 48

export default async function LatestPage({
  searchParams,
}: {
  searchParams: Promise<{ page?: string }>
}) {
  const sp = await searchParams
  const page = Math.max(1, parseInt(sp.page ?? '1', 10) || 1)
  const from = (page - 1) * PAGE_SIZE
  const to = from + PAGE_SIZE - 1

  const { data, count } = await supabase
    .from('transcripts')
    .select('vid,channel,channel_slug,title,published_at,summary,summarized_at', {
      count: 'exact',
    })
    .not('summary', 'is', null)
    .order('summarized_at', { ascending: false, nullsFirst: false })
    .range(from, to)

  const items = (data ?? []) as Transcript[]
  const total = count ?? items.length

  return (
    <main className="max-w-7xl mx-auto px-4 sm:px-6 py-8">
      <Link href="/" className="text-xs text-zinc-500 hover:text-zinc-200">
        ← 홈
      </Link>
      <header className="mt-3 mb-8">
        <h1 className="text-2xl sm:text-3xl font-bold tracking-tight">📺 최신 요약</h1>
        <p className="text-sm text-zinc-500 mt-1">
          전체 {total}편 · {page}/{Math.max(1, Math.ceil(total / PAGE_SIZE))} 페이지
        </p>
      </header>

      {items.length === 0 ? (
        <div className="rounded-lg border border-zinc-800 bg-zinc-900/50 p-8 text-center text-zinc-500">
          이 페이지에 요약이 없어요.
        </div>
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
          {items.map((t) => (
            <VideoCard key={t.vid} t={t} />
          ))}
        </div>
      )}

      <Pagination basePath="/latest" page={page} pageSize={PAGE_SIZE} total={total} />
    </main>
  )
}

import Link from 'next/link'
import { supabase } from '@/lib/supabase'
import { STOCK_ECON_SLUGS, getChannelMeta } from '@/lib/channels'
import { InfiniteList } from '@/components/InfiniteList'

export const revalidate = 60

type ChannelStat = {
  slug: string
  count_summarized: number
  latest_published_at: string | null
}

async function fetchChannelStats(): Promise<ChannelStat[]> {
  // summary 있는 행의 (channel_slug, published_at) 단일 쿼리로 수집 후 JS 집계.
  // 채널 수 × 2쿼리(16 round-trip) → 1쿼리(+1000행 초과 시 range 페이지네이션).
  const rows: { channel_slug: string; published_at: string | null }[] = []
  const PAGE = 1000
  for (let from = 0; ; from += PAGE) {
    const { data, error } = await supabase
      .from('transcripts')
      .select('channel_slug,published_at')
      .not('summary', 'is', null)
      .range(from, from + PAGE - 1)
    if (error || !data || data.length === 0) break
    rows.push(...data)
    if (data.length < PAGE) break
  }

  const agg = new Map<string, { count: number; latest: string | null }>()
  for (const r of rows) {
    const a = agg.get(r.channel_slug) ?? { count: 0, latest: null }
    a.count += 1
    if (r.published_at && (a.latest === null || r.published_at > a.latest)) {
      a.latest = r.published_at
    }
    agg.set(r.channel_slug, a)
  }

  return STOCK_ECON_SLUGS.map((slug) => {
    const a = agg.get(slug)
    return {
      slug,
      count_summarized: a?.count ?? 0,
      latest_published_at: a?.latest ?? null,
    }
  })
}

export default async function HomePage() {
  const channelStats = await fetchChannelStats()

  return (
    <main className="max-w-7xl mx-auto px-4 sm:px-6 py-8">
      <header className="mb-10">
        <h1 className="text-2xl sm:text-3xl font-bold tracking-tight">
          📺 주식·경제 요약 다이제스트
        </h1>
        <p className="text-sm text-zinc-500 mt-1">
          7개 채널 영상의 매수·매도·관전 포인트를 한 곳에 모아봅니다 · 자동 갱신 60s
        </p>
      </header>

      <section className="mb-12">
        <h2 className="text-lg font-semibold mb-4 text-zinc-200">채널</h2>
        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 xl:grid-cols-7 gap-3">
          {channelStats.map((s) => {
            const ch = getChannelMeta(s.slug)
            return (
              <Link
                key={s.slug}
                href={`/channel/${s.slug}`}
                className="group block rounded-xl border border-zinc-800 hover:border-zinc-600 bg-zinc-900/40 p-4 transition-all hover:-translate-y-0.5"
                style={{ borderTopColor: ch.hex, borderTopWidth: 3 }}
              >
                <div className="text-sm font-semibold text-zinc-100 mb-1 group-hover:text-white">
                  {ch.name}
                </div>
                <div className="text-2xl font-bold" style={{ color: ch.hex }}>
                  {s.count_summarized}
                </div>
                <div className="text-[10px] text-zinc-500 mt-0.5">요약</div>
                {s.latest_published_at && (
                  <div className="text-[10px] text-zinc-600 mt-1">
                    최근 {s.latest_published_at}
                  </div>
                )}
              </Link>
            )
          })}
        </div>
      </section>

      <section>
        <h2 className="text-lg font-semibold text-zinc-200 mb-4">최신 요약</h2>
        <InfiniteList mode="latest-summarized" pageSize={20} />
      </section>
    </main>
  )
}

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
  const stats = await Promise.all(
    STOCK_ECON_SLUGS.map(async (slug) => {
      const { count } = await supabase
        .from('transcripts')
        .select('vid', { count: 'exact', head: true })
        .eq('channel_slug', slug)
        .not('summary', 'is', null)

      const { data: latest } = await supabase
        .from('transcripts')
        .select('published_at')
        .eq('channel_slug', slug)
        .order('published_at', { ascending: false, nullsFirst: false })
        .limit(1)

      return {
        slug,
        count_summarized: count ?? 0,
        latest_published_at: latest?.[0]?.published_at ?? null,
      }
    })
  )
  return stats
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

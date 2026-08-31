import Link from 'next/link'
import { supabase, Transcript } from '@/lib/supabase'
import { STOCK_ECON_SLUGS, getChannelMeta } from '@/lib/channels'
import { SearchableFeed } from '@/components/SearchableFeed'
import { SHORTS_THRESHOLD_SEC } from '@/components/ShortsFilter'

export const revalidate = 3600

type ChannelStat = {
  slug: string
  count_summarized: number
  latest_published_at: string | null
}

async function fetchChannelStats(): Promise<ChannelStat[]> {
  // 집계는 DB에서 한다(channel_stats RPC → 채널 수만큼의 행만 전송).
  // 예전엔 summary 있는 행 전체를 1000개씩 끌어와 JS로 집계했는데,
  // 요약 1,075건 기준 1,075행 전송 + 1.5초였고 요약이 늘수록 선형으로 느려졌다.
  const { data, error } = await supabase.rpc('channel_stats')
  // 에러를 삼키면 0 결과가 ISR에 캐시됨(DB 일시 장애 때 홈 카운트 0 고착) → throw로 렌더 실패시켜 이전 캐시 유지
  if (error) throw error

  const agg = new Map<string, { count: number; latest: string | null }>()
  for (const r of (data ?? []) as {
    channel_slug: string
    count_summarized: number
    latest_published_at: string | null
  }[]) {
    agg.set(r.channel_slug, { count: r.count_summarized, latest: r.latest_published_at })
  }

  // 요약 0건 채널은 숨긴다. 카드를 눌러도 빈 목록만 나와서 헛걸음이 된다
  // (새로 등록한 채널은 첫 요약이 쌓이는 순간 자동으로 나타난다).
  return STOCK_ECON_SLUGS.map((slug) => {
    const a = agg.get(slug)
    return {
      slug,
      count_summarized: a?.count ?? 0,
      latest_published_at: a?.latest ?? null,
    }
  }).filter((s) => s.count_summarized > 0)
}

// 최신 피드 첫 페이지를 서버에서 미리 가져온다.
// 예전엔 피드가 클라이언트 마운트 후에야 RPC를 쳐서, 사용자는 JS 로드 + 왕복이 끝날 때까지
// 빈 화면을 봤다. ISR(1h)로 캐시되므로 대부분의 방문에서 추가 비용도 없다.
//
// 쇼츠 숨김이 기본값이므로 서버 데이터도 같은 기준으로 가져온다.
// 기준이 어긋나면 기본 사용자가 카드를 봤다가 다시 로딩되는 깜빡임을 겪는다.
async function fetchInitialFeed(): Promise<Transcript[]> {
  const { data, error } = await supabase.rpc('feed_summaries', {
    p_channel: null,
    p_limit: 20,
    p_offset: 0,
    p_min_duration: SHORTS_THRESHOLD_SEC,
  })
  if (error) throw error
  return (data ?? []) as Transcript[]
}

export default async function HomePage() {
  // 채널 통계와 첫 피드를 동시에 — 두 왕복을 직렬로 기다리지 않는다.
  const [channelStats, initialFeed] = await Promise.all([
    fetchChannelStats(),
    fetchInitialFeed(),
  ])

  return (
    <main className="max-w-7xl mx-auto px-4 sm:px-6 py-8">
      <header className="mb-10">
        <h1 className="text-2xl sm:text-3xl font-bold tracking-tight">
          📺 주식·경제 요약 다이제스트
        </h1>
        {/* 채널 수는 하드코딩하면 채널이 늘 때마다 어긋난다(실제 11개인데 "7개"로 방치됐었다).
            갱신 주기도 revalidate 상수에서 직접 뽑아 문구와 동작이 갈라지지 않게 한다. */}
        <p className="text-sm text-zinc-500 mt-1">
          {STOCK_ECON_SLUGS.length}개 채널 영상의 매수·매도·관전 포인트를 한 곳에 모아봅니다 ·{' '}
          {revalidate / 3600}시간마다 갱신
        </p>
      </header>

      <section className="mb-12">
        <h2 className="text-lg font-semibold mb-4 text-zinc-200">채널</h2>
        {/* 채널 11개 기준. xl:7이면 둘째 줄에 4개만 남아 어색하다 — 6열이면 6+5로 균형이 맞는다. */}
        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 xl:grid-cols-6 gap-3">
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
        <SearchableFeed initialItems={initialFeed} />
      </section>
    </main>
  )
}

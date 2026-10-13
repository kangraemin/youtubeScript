import Link from 'next/link'
import { fetchFeedPage } from '@/lib/feed'
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
    agg.set(r.channel_slug, {
      count: r.count_summarized,
      latest: r.latest_published_at,
    })
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
  return fetchFeedPage({minDuration: SHORTS_THRESHOLD_SEC})
}

export default async function HomePage() {
  // 채널 통계와 첫 피드를 동시에 — 두 왕복을 직렬로 기다리지 않는다.
  const [channelStats, initialFeed] = await Promise.all([
    fetchChannelStats(),
    fetchInitialFeed(),
  ])

  return (
    <main className="page-shell">
      <header className="home-intro">
        <p className="eyebrow">YOUR DAILY ECONOMY</p>
        <h1>오늘의 경제 브리핑</h1>
        <p>
          {channelStats.length}개 경제 채널의 이야기. 매매 발언부터 경제
          개념까지.
        </p>
      </header>
      <nav className="channel-nav" aria-label={`채널 ${channelStats.length}개`}>
        <Link href="/" className="channel-chip is-active" aria-current="page">
          전체 채널
        </Link>
        {channelStats.map((s) => (
          <Link
            key={s.slug}
            href={`/channel/${s.slug}`}
            className="channel-chip"
          >
            {getChannelMeta(s.slug).name}
            <span>{s.count_summarized}</span>
          </Link>
        ))}
      </nav>
      <section aria-labelledby="feed-heading">
        <div className="feed-heading">
          <h2 id="feed-heading">지금 읽을 경제 이야기</h2>
          <span>{revalidate / 3600}시간마다 갱신</span>
        </div>
        <SearchableFeed initialItems={initialFeed} />
      </section>
      <footer className="site-footer">
        경제 다이제스트 · 영상의 발언과 맥락을 함께 읽어요.
      </footer>
    </main>
  )
}

import Link from 'next/link'
import { supabase } from '@/lib/supabase'
import { getChannelMeta } from '@/lib/channels'
import { InfiniteList } from '@/components/InfiniteList'

export const revalidate = 60

export default async function ChannelPage({
  params,
}: {
  params: Promise<{ slug: string }>
}) {
  const { slug } = await params

  // 헤더의 채널명 노출용 + 요약 카운트
  const [headRes, summarizedCountRes] = await Promise.all([
    supabase
      .from('transcripts')
      .select('channel')
      .eq('channel_slug', slug)
      .limit(1),
    supabase
      .from('transcripts')
      .select('vid', { count: 'exact', head: true })
      .eq('channel_slug', slug)
      .not('summary', 'is', null),
  ])
  const ch = getChannelMeta(slug, headRes.data?.[0]?.channel ?? slug)
  const totalSummarized = summarizedCountRes.count ?? 0

  return (
    <main className="page-shell">
      <Link href="/" className="back-link">
        ← 홈
      </Link>

      <header className="page-intro">
        <h1 className="page-title">{ch.name}</h1>
        <p className="page-description">요약 {totalSummarized}편</p>
      </header>

      <InfiniteList
        mode="channel-summarized"
        channelSlug={slug}
        showChannel={false}
        pageSize={20}
      />
    </main>
  )
}

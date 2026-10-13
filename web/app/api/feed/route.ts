import { fetchFeedPage } from '@/lib/feed'
export async function GET(request: Request) {
  const p = new URL(request.url).searchParams
  const number = (key: string, fallback: number, max: number) => {
    const raw = p.get(key)
    const value = raw === null ? fallback : Number(raw)
    return Number.isInteger(value) && value >= 0
      ? Math.min(value, max)
      : fallback
  }
  try {
    const items = await fetchFeedPage({
      channel: p.get('channel') || null,
      limit: Math.max(1, number('limit', 20, 50)),
      offset: number('offset', 0, 100000),
      minDuration: number('minDuration', 0, 86400),
    })
    return Response.json(items, {
      headers: {
        'Cache-Control': 'public, s-maxage=60, stale-while-revalidate=120',
      },
    })
  } catch {
    return Response.json(
      { error: '요약을 불러오지 못했어요.' },
      { status: 503 },
    )
  }
}

'use client'

import { useCallback, useEffect, useRef, useState } from 'react'
import { supabase, Transcript } from '@/lib/supabase'
import { VideoCard } from '@/components/VideoCard'

type Mode = 'latest-summarized' | 'channel-summarized'

type Props = {
  mode: Mode
  // channel-* 모드에서만 사용
  channelSlug?: string
  showChannel?: boolean
  pageSize?: number
}

export function InfiniteList({ mode, channelSlug, showChannel = true, pageSize = 20 }: Props) {
  const [items, setItems] = useState<Transcript[]>([])
  const [done, setDone] = useState(false)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const sentinelRef = useRef<HTMLDivElement>(null)
  // 호출 중복 방지용 (effect race + observer rapid trigger)
  const inFlight = useRef(false)

  const loadMore = useCallback(async () => {
    if (inFlight.current || done) return
    inFlight.current = true
    setLoading(true)
    setError(null)
    try {
      const from = items.length
      const to = from + pageSize - 1
      let q = supabase
        .from('transcripts')
        .select('vid,channel,channel_slug,title,published_at,summary,summarized_at')

      if (mode === 'latest-summarized') {
        q = q
          .not('summary', 'is', null)
          .order('published_at', { ascending: false, nullsFirst: false })
      } else if (channelSlug) {
        // channel-summarized — 요약된 영상만, published_at desc
        q = q
          .eq('channel_slug', channelSlug)
          .not('summary', 'is', null)
          .order('published_at', { ascending: false, nullsFirst: false })
      }

      const { data, error: err } = await q.range(from, to)
      if (err) {
        setError(err.message)
        return
      }
      const next = (data ?? []) as Transcript[]
      setItems((prev) => [...prev, ...next])
      if (next.length < pageSize) setDone(true)
    } finally {
      setLoading(false)
      inFlight.current = false
    }
  }, [items.length, done, mode, channelSlug, pageSize])

  // mount + 모드/필터 변경 시 상태 리셋 후 첫 페이지 fetch.
  useEffect(() => {
    inFlight.current = false
    setItems([])
    setDone(false)
    setError(null)
    const id = requestAnimationFrame(() => loadMore())
    return () => cancelAnimationFrame(id)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [mode, channelSlug])

  // 무한 스크롤 — sentinel 화면 진입 시 next page
  useEffect(() => {
    if (done) return
    const el = sentinelRef.current
    if (!el) return
    const obs = new IntersectionObserver(
      (entries) => {
        if (entries[0]?.isIntersecting) loadMore()
      },
      { rootMargin: '400px 0px' } // 끝 도달 전 미리 fetch
    )
    obs.observe(el)
    return () => obs.disconnect()
  }, [loadMore, done])

  return (
    <>
      {items.length === 0 && !loading ? (
        <div className="rounded-lg border border-zinc-800 bg-zinc-900/50 p-8 text-center text-zinc-500">
          표시할 영상이 없어요.
        </div>
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
          {items.map((t) => (
            <VideoCard key={t.vid} t={t} showChannel={showChannel} />
          ))}
        </div>
      )}

      {/* Sentinel — 끝나면 안 그림 */}
      {!done && (
        <div ref={sentinelRef} className="mt-8 flex items-center justify-center py-6">
          <span className="text-sm text-zinc-500">
            {loading ? '불러오는 중…' : '아래로 스크롤'}
          </span>
        </div>
      )}

      {done && items.length > 0 && (
        <div className="mt-8 text-center text-xs text-zinc-600">
          마지막 페이지 · 총 {items.length}편
        </div>
      )}

      {error && (
        <div className="mt-4 text-center text-xs text-rose-400">
          로드 실패: {error}
          <button
            onClick={() => {
              inFlight.current = false
              loadMore()
            }}
            className="ml-2 underline"
          >
            다시 시도
          </button>
        </div>
      )}
    </>
  )
}

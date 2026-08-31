'use client'

import { useCallback, useEffect, useRef, useState } from 'react'
import { supabase, Transcript } from '@/lib/supabase'
import { VideoCard } from '@/components/VideoCard'
import { ShortsFilter, SHORTS_THRESHOLD_SEC, readHideShorts } from '@/components/ShortsFilter'

type Mode = 'latest-summarized' | 'channel-summarized' | 'search'

type Props = {
  mode: Mode
  // channel-* 모드에서만 사용
  channelSlug?: string
  // search 모드에서만 사용
  searchQuery?: string
  showChannel?: boolean
  pageSize?: number
}

export function InfiniteList({
  mode,
  channelSlug,
  searchQuery,
  showChannel = true,
  pageSize = 20,
}: Props) {
  const [items, setItems] = useState<Transcript[]>([])
  const [done, setDone] = useState(false)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  // 쇼츠 숨기기. 저장값은 마운트 후 읽어 hydration 불일치를 피한다.
  const [hideShorts, setHideShorts] = useState(false)
  const sentinelRef = useRef<HTMLDivElement>(null)
  // 호출 중복 방지용 (effect race + observer rapid trigger)
  const inFlight = useRef(false)
  // 서버에서 받아온 원본 행 수. 검색 모드는 클라이언트에서 쇼츠를 걸러내므로
  // items.length를 offset으로 쓰면 걸러낸 만큼 범위가 겹쳐 중복이 생긴다.
  const fetchedCount = useRef(0)

  useEffect(() => {
    const saved = readHideShorts()
    if (saved) setHideShorts(true)
  }, [])

  // 상세→뒤로 시 재fetch 방지: items+done+scroll을 sessionStorage에 보존.
  // 쇼츠 필터가 키에 들어가야 필터별 목록이 서로 섞이지 않는다.
  const storageKey = `il:${mode}:${channelSlug ?? ''}:${searchQuery ?? ''}:${hideShorts ? 'nosh' : 'all'}`

  const loadMore = useCallback(async () => {
    if (inFlight.current || done) return
    inFlight.current = true
    setLoading(true)
    setError(null)
    try {
      const from = fetchedCount.current
      const to = from + pageSize - 1
      const cols = 'vid,channel,channel_slug,title,published_at,summary,summarized_at'

      let data: Transcript[] | null = null
      let err: { message: string } | null = null

      if (mode === 'search') {
        // 검색 RPC는 길이 조건을 받지 않으므로 결과를 클라이언트에서 걸러낸다.
        const r = await supabase
          .rpc('search_transcripts', { q_input: searchQuery ?? '' })
          .select(cols)
          .range(from, to)
        data = r.data as Transcript[] | null
        err = r.error
      } else {
        // 브라우즈 피드(latest/channel)는 경량 RPC — headline + 매수/매도/관전/용어 개수만.
        // summary(13섹션 전체 jsonb)를 끌어오지 않아 페이로드가 작다.
        const r = await supabase.rpc('feed_summaries', {
          p_channel: mode === 'channel-summarized' ? channelSlug ?? null : null,
          p_limit: pageSize,
          p_offset: from,
          p_min_duration: hideShorts ? SHORTS_THRESHOLD_SEC : 0,
        })
        data = r.data as Transcript[] | null
        err = r.error
      }

      if (err) {
        setError(err.message)
        return
      }
      const raw = (data ?? []) as Transcript[]
      fetchedCount.current += raw.length
      // 검색 RPC는 길이 조건을 못 받으므로 여기서 거른다. 길이를 모르는 행(null/-1)도 함께 제외.
      const next =
        mode === 'search' && hideShorts
          ? raw.filter((t) => (t.duration_sec ?? -1) >= SHORTS_THRESHOLD_SEC)
          : raw
      setItems((prev) => [...prev, ...next])
      // 끝 판정은 걸러낸 뒤가 아니라 서버가 준 원본 개수로 해야 조기 종료되지 않는다.
      if (raw.length < pageSize) setDone(true)
    } finally {
      setLoading(false)
      inFlight.current = false
    }
  }, [done, mode, channelSlug, searchQuery, pageSize, hideShorts])

  // mount/키 변경: sessionStorage 캐시 있으면 복원(+스크롤), 없으면 리셋 후 첫 페이지 fetch.
  useEffect(() => {
    inFlight.current = false
    setError(null)
    let restored = false
    try {
      const raw = sessionStorage.getItem(storageKey)
      if (raw) {
        const c = JSON.parse(raw) as {
          items: Transcript[]
          done: boolean
          scrollY: number
          fetched?: number
        }
        if (c.items?.length) {
          setItems(c.items)
          setDone(c.done)
          // 복원 시 offset도 함께 되돌린다. 없으면(구버전 캐시) items 수로 근사.
          fetchedCount.current = c.fetched ?? c.items.length
          restored = true
          requestAnimationFrame(() => window.scrollTo(0, c.scrollY || 0))
        }
      }
    } catch {
      // 손상된 캐시 무시
    }
    if (!restored) {
      setItems([])
      setDone(false)
      fetchedCount.current = 0
      const id = requestAnimationFrame(() => loadMore())
      return () => cancelAnimationFrame(id)
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [mode, channelSlug, searchQuery, hideShorts])

  // items/done 변경 + 스크롤(throttle) 시 sessionStorage 기록.
  useEffect(() => {
    if (items.length === 0) return
    const save = () => {
      try {
        sessionStorage.setItem(
          storageKey,
          JSON.stringify({ items, done, scrollY: window.scrollY, fetched: fetchedCount.current })
        )
      } catch {
        // 용량 초과 등 무시
      }
    }
    save()
    let t: ReturnType<typeof setTimeout> | null = null
    const onScroll = () => {
      if (t) return
      t = setTimeout(() => {
        t = null
        save()
      }, 250)
    }
    window.addEventListener('scroll', onScroll, { passive: true })
    return () => {
      window.removeEventListener('scroll', onScroll)
      if (t) clearTimeout(t)
    }
  }, [items, done, storageKey])

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
      <div className="mb-4 flex items-center justify-end">
        <ShortsFilter value={hideShorts} onChange={setHideShorts} />
      </div>

      {items.length === 0 && !loading ? (
        <div className="rounded-lg border border-zinc-800 bg-zinc-900/50 p-8 text-center text-zinc-500">
          {hideShorts ? '3분 이상 영상이 없어요. 필터를 꺼보세요.' : '표시할 영상이 없어요.'}
        </div>
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
          {items.map((t) => (
            <VideoCard
              key={t.vid}
              t={t}
              showChannel={showChannel}
              searchQuery={mode === 'search' ? searchQuery : undefined}
            />
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

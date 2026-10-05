'use client'

import { useState, useEffect } from 'react'
import { InfiniteList } from '@/components/InfiniteList'
import { Transcript } from '@/lib/supabase'

// initialItems: 서버에서 미리 가져온 최신 피드 첫 페이지. 검색 모드에는 쓰지 않는다.
export function SearchableFeed({ initialItems }: { initialItems?: Transcript[] }) {
  const [input, setInput] = useState('')
  const [q, setQ] = useState('')

  // 검색어를 URL(?q=)과 동기화한다. 예전엔 useState에만 있어서 상세에 들어갔다 돌아오거나
  // 링크로 공유하면 검색이 사라졌다. useSearchParams는 ISR 페이지에서 Suspense 경계를
  // 요구하므로 마운트 후 window.location에서 읽는다.
  useEffect(() => {
    const initial = new URLSearchParams(window.location.search).get('q') ?? ''
    if (initial) {
      setInput(initial)
      setQ(initial.trim().length >= 2 ? initial.trim() : '')
    }
  }, [])

  useEffect(() => {
    const tm = setTimeout(() => {
      const v = input.trim()
      setQ(v.length >= 2 ? v : '')
    }, 350)
    return () => clearTimeout(tm)
  }, [input])

  useEffect(() => {
    const url = new URL(window.location.href)
    if (q) url.searchParams.set('q', q)
    else url.searchParams.delete('q')
    window.history.replaceState(window.history.state, '', url)
  }, [q])

  const tooShort = input.trim().length === 1

  return (
    <>
      <input
        type="search"
        aria-label="회사·티커 검색"
        value={input}
        onChange={(e) => setInput(e.target.value)}
        placeholder="회사·티커 검색 (예: 삼성전자, 엔비디아, TSLA)"
        className="w-full min-h-11 mb-2 rounded-lg border border-zinc-700 bg-zinc-900 px-4 py-2.5 text-base sm:text-sm text-zinc-100 placeholder:text-zinc-400 focus:border-[var(--accent)] transition-colors"
      />
      {tooShort && <div className="text-xs text-zinc-400 mb-3">2자 이상 입력하세요</div>}
      {q && <div className="text-xs text-zinc-400 mb-3">‘{q}’ 검색 결과</div>}
      {q ? (
        <InfiniteList key={`s:${q}`} mode="search" searchQuery={q} pageSize={20} />
      ) : (
        <InfiniteList
          key="latest"
          mode="latest-summarized"
          pageSize={20}
          initialItems={initialItems}
        />
      )}
    </>
  )
}

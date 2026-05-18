'use client'

import { useState, useEffect } from 'react'
import { InfiniteList } from '@/components/InfiniteList'

export function SearchableFeed() {
  const [input, setInput] = useState('')
  const [q, setQ] = useState('')

  useEffect(() => {
    const tm = setTimeout(() => {
      const v = input.trim()
      setQ(v.length >= 2 ? v : '')
    }, 350)
    return () => clearTimeout(tm)
  }, [input])

  const tooShort = input.trim().length === 1

  return (
    <>
      <input
        value={input}
        onChange={(e) => setInput(e.target.value)}
        placeholder="회사·티커 검색 (예: 삼성전자, 엔비디아, TSLA)"
        className="w-full mb-2 rounded border border-zinc-800 bg-zinc-900 px-4 py-2.5 text-sm text-zinc-100 placeholder:text-zinc-500 focus:border-violet-500 outline-none transition-colors"
      />
      {tooShort && <div className="text-xs text-zinc-500 mb-3">2자 이상 입력하세요</div>}
      {q && <div className="text-xs text-zinc-500 mb-3">‘{q}’ 검색 결과</div>}
      {q ? (
        <InfiniteList key={`s:${q}`} mode="search" searchQuery={q} pageSize={20} />
      ) : (
        <InfiniteList key="latest" mode="latest-summarized" pageSize={20} />
      )}
    </>
  )
}

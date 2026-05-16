import Link from 'next/link'
import { InfiniteList } from '@/components/InfiniteList'

export const revalidate = 60

export default function LatestPage() {
  return (
    <main className="max-w-7xl mx-auto px-4 sm:px-6 py-8">
      <Link href="/" className="text-xs text-zinc-500 hover:text-zinc-200">
        ← 홈
      </Link>
      <header className="mt-3 mb-8">
        <h1 className="text-2xl sm:text-3xl font-bold tracking-tight">📺 최신 요약</h1>
        <p className="text-sm text-zinc-500 mt-1">요약된 모든 영상 — 최신 요약 순</p>
      </header>
      <InfiniteList mode="latest-summarized" pageSize={20} />
    </main>
  )
}

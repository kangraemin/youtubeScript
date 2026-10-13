import Link from 'next/link'
import { InfiniteList } from '@/components/InfiniteList'

export const revalidate = 3600

export default function LatestPage() {
  return (
    <main className="page-shell">
      <Link href="/" className="back-link">
        ← 홈
      </Link>
      <header className="page-intro">
        <h1 className="page-title">최신 요약</h1>
        <p className="page-description">요약된 모든 영상 — 최신 요약 순</p>
      </header>
      <InfiniteList mode="latest-summarized" pageSize={20} />
    </main>
  )
}

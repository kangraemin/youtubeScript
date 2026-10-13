import Link from 'next/link'

export function SiteHeader() {
  return (
    <header className="site-header">
      <div className="site-header-inner">
        <Link href="/" className="brand" aria-label="경제 다이제스트 홈">
          <span className="brand-mark" aria-hidden="true">
            <i />
            <i />
            <i />
          </span>
          <span>
            경제 다이제스트
            <span className="brand-caption">보고 듣던 경제, 이제 읽다</span>
          </span>
        </Link>
        <Link href="/latest" className="header-link">
          전체 요약 <span aria-hidden="true">↗</span>
        </Link>
      </div>
    </header>
  )
}

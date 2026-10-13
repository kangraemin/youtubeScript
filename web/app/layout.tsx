import './globals.css'
import type { Metadata } from 'next'
import { SiteHeader } from '@/components/SiteHeader'
import { RouteProgress } from '@/components/RouteProgress'

export const metadata: Metadata = {
  title: 'YouTube 주식·경제 요약',
  description:
    '긴 경제 영상에서 매수·매도 발언과 알아둘 경제 지식을 골라 읽어요.',
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="ko">
      <body className="min-h-screen">
        <RouteProgress />
        <SiteHeader />
        {children}
      </body>
    </html>
  )
}

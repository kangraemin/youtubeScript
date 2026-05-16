import './globals.css'
import type { Metadata } from 'next'

export const metadata: Metadata = {
  title: 'YouTube 주식·경제 요약',
  description: '유튜브 주식·경제 채널 transcript 자동 요약',
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="ko">
      <body className="bg-bg text-zinc-100 min-h-screen">{children}</body>
    </html>
  )
}

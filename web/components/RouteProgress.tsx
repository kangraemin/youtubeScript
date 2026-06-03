'use client'

import { Suspense, useEffect, useRef, useState } from 'react'
import { usePathname, useSearchParams } from 'next/navigation'

// 클라이언트 네비게이션 시 상단에 잠깐 progress bar를 표시한다.
// 경로/쿼리가 바뀌면 0→90%까지 차오르다가, 새 화면 커밋(이 컴포넌트 리렌더) 시 100%로 마무리.
function RouteProgressInner() {
  const pathname = usePathname()
  const search = useSearchParams()
  const key = pathname + '?' + search.toString()

  const [progress, setProgress] = useState(0)
  const [visible, setVisible] = useState(false)
  const first = useRef(true)
  const timers = useRef<ReturnType<typeof setTimeout>[]>([])

  useEffect(() => {
    if (first.current) {
      first.current = false
      return
    }
    // 새 라우트 진입: 바 표시 후 빠르게 차오름
    timers.current.forEach(clearTimeout)
    timers.current = []
    setVisible(true)
    setProgress(15)
    timers.current.push(setTimeout(() => setProgress(65), 80))
    timers.current.push(setTimeout(() => setProgress(90), 300))
    // 화면 커밋(다음 effect 사이클)에서 100% 후 숨김
    timers.current.push(
      setTimeout(() => {
        setProgress(100)
        timers.current.push(
          setTimeout(() => {
            setVisible(false)
            setProgress(0)
          }, 200)
        )
      }, 500)
    )
    return () => timers.current.forEach(clearTimeout)
  }, [key])

  return (
    <div
      aria-hidden
      className="fixed top-0 left-0 right-0 z-[100] h-0.5 pointer-events-none"
      style={{ opacity: visible ? 1 : 0, transition: 'opacity 200ms' }}
    >
      <div
        className="h-full bg-amber-400 shadow-[0_0_8px_rgba(251,191,36,0.7)]"
        style={{ width: `${progress}%`, transition: 'width 200ms ease-out' }}
      />
    </div>
  )
}

export function RouteProgress() {
  // useSearchParams는 Suspense 경계가 필요(빌드 시 CSR bailout 방지)
  return (
    <Suspense fallback={null}>
      <RouteProgressInner />
    </Suspense>
  )
}

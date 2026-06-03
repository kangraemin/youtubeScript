'use client'

import { Suspense, useEffect, useRef, useState } from 'react'
import { usePathname, useSearchParams } from 'next/navigation'

// 클라이언트 네비게이션 시 상단에 progress bar를 표시한다.
// 내부 링크를 클릭하는 즉시(네비 시작) 바가 차오르고, 새 경로가 커밋되면(usePathname 변화) 100%로 마무리한다.
// usePathname 변화는 네비 "완료" 시점이라, 느린 상세 진입(1.5s) 동안 바를 보여주려면 클릭 시점에 시작해야 한다.
function RouteProgressInner() {
  const pathname = usePathname()
  const search = useSearchParams()
  const key = pathname + '?' + search.toString()

  const [progress, setProgress] = useState(0)
  const [visible, setVisible] = useState(false)
  const first = useRef(true)
  const active = useRef(false)
  const timers = useRef<ReturnType<typeof setTimeout>[]>([])

  const clearTimers = () => {
    timers.current.forEach(clearTimeout)
    timers.current = []
  }

  const finish = () => {
    if (!active.current) return
    active.current = false
    clearTimers()
    setProgress(100)
    timers.current.push(
      setTimeout(() => {
        setVisible(false)
        setProgress(0)
      }, 220)
    )
  }

  const start = () => {
    clearTimers()
    active.current = true
    setVisible(true)
    setProgress(8)
    timers.current.push(setTimeout(() => setProgress(45), 90))
    timers.current.push(setTimeout(() => setProgress(75), 300))
    timers.current.push(setTimeout(() => setProgress(90), 800))
    // 안전장치: 네비가 끝내 완료되지 않아도 10s 후 정리
    timers.current.push(setTimeout(() => finish(), 10000))
  }

  // (a) 내부 링크 클릭 즉시 시작 — capture 단계로 Link 핸들러보다 먼저 잡는다.
  useEffect(() => {
    const onClick = (e: MouseEvent) => {
      if (e.defaultPrevented) return
      if (e.button !== 0 || e.metaKey || e.ctrlKey || e.shiftKey || e.altKey) return
      const a = (e.target as HTMLElement)?.closest?.('a')
      if (!a) return
      const href = a.getAttribute('href')
      if (!href) return
      if (a.target && a.target !== '_self') return // 새 탭 제외
      if (a.hasAttribute('download')) return
      let url: URL
      try {
        url = new URL(a.href, window.location.href)
      } catch {
        return
      }
      if (url.origin !== window.location.origin) return // 외부 제외
      if (
        url.pathname + url.search ===
        window.location.pathname + window.location.search
      )
        return // 동일 경로(해시 등) 제외
      start()
    }
    document.addEventListener('click', onClick, true)
    return () => document.removeEventListener('click', onClick, true)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  // (b) 네비 완료(경로/쿼리 변화) → finish. 최초 마운트는 skip.
  useEffect(() => {
    if (first.current) {
      first.current = false
      return
    }
    finish()
    return () => clearTimers()
    // eslint-disable-next-line react-hooks/exhaustive-deps
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

'use client'

// 쇼츠 숨기기 토글. 선택 상태를 localStorage에 보존해 페이지 이동·재방문에도 유지된다.
// 임계값은 크롤러의 min_duration_sec 정책(180초)과 같은 값을 쓴다.

import { useEffect, useState } from 'react'

export const SHORTS_THRESHOLD_SEC = 180
const STORAGE_KEY = 'hideShorts'

/** 저장된 쇼츠 필터 상태를 읽는다. SSR에서는 항상 false. */
export function readHideShorts(): boolean {
  if (typeof window === 'undefined') return false
  try {
    return window.localStorage.getItem(STORAGE_KEY) === '1'
  } catch {
    return false
  }
}

type Props = {
  value: boolean
  onChange: (next: boolean) => void
}

export function ShortsFilter({ value, onChange }: Props) {
  // hydration 불일치 방지 — 마운트 전에는 서버와 같은 기본 모습으로 그린다.
  const [mounted, setMounted] = useState(false)
  useEffect(() => setMounted(true), [])

  const on = mounted && value

  return (
    <button
      type="button"
      role="switch"
      aria-checked={on}
      aria-label="쇼츠 숨기기"
      onClick={() => {
        const next = !value
        onChange(next)
        try {
          window.localStorage.setItem(STORAGE_KEY, next ? '1' : '0')
        } catch {
          // 프라이빗 모드 등 — 저장 실패해도 이번 세션 동작은 유지
        }
      }}
      className={`inline-flex items-center gap-2 rounded-full border px-3 py-1.5 text-sm transition-colors ${
        on
          ? 'border-sky-500/60 bg-sky-500/15 text-sky-300'
          : 'border-zinc-700 bg-zinc-900/60 text-zinc-400 hover:border-zinc-600 hover:text-zinc-300'
      }`}
    >
      <span
        className={`inline-block h-4 w-7 shrink-0 rounded-full p-0.5 transition-colors ${
          on ? 'bg-sky-500' : 'bg-zinc-700'
        }`}
      >
        <span
          className={`block h-3 w-3 rounded-full bg-white transition-transform ${
            on ? 'translate-x-3' : 'translate-x-0'
          }`}
        />
      </span>
      쇼츠 숨기기
      <span className="text-xs text-zinc-500">3분 미만</span>
    </button>
  )
}

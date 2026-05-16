import Link from 'next/link'

type Props = {
  basePath: string
  page: number
  pageSize: number
  total: number
  // 추가 query string (예: filter=summarized) — 페이지 외 파라미터 유지
  extraQuery?: Record<string, string | undefined>
}

function buildHref(basePath: string, page: number, extra: Record<string, string | undefined>) {
  const qs = new URLSearchParams()
  if (page > 1) qs.set('page', String(page))
  for (const [k, v] of Object.entries(extra)) {
    if (v != null && v !== '') qs.set(k, v)
  }
  const s = qs.toString()
  return s ? `${basePath}?${s}` : basePath
}

export function Pagination({ basePath, page, pageSize, total, extraQuery = {} }: Props) {
  const totalPages = Math.max(1, Math.ceil(total / pageSize))
  if (totalPages <= 1) return null

  const prevPage = Math.max(1, page - 1)
  const nextPage = Math.min(totalPages, page + 1)

  // 페이지 번호 좁은 윈도우 (현재 ±2)
  const window: number[] = []
  for (let i = Math.max(1, page - 2); i <= Math.min(totalPages, page + 2); i++) {
    window.push(i)
  }
  if (window[0] !== 1) window.unshift(1)
  if (window[window.length - 1] !== totalPages) window.push(totalPages)

  const linkCls =
    'min-w-[2.25rem] h-9 px-2 inline-flex items-center justify-center rounded-md text-sm border border-zinc-800 hover:border-zinc-600 bg-zinc-900/40 hover:bg-zinc-800/40 text-zinc-300'
  const activeCls =
    'min-w-[2.25rem] h-9 px-2 inline-flex items-center justify-center rounded-md text-sm bg-zinc-100 text-zinc-950 font-semibold'
  const disabledCls =
    'min-w-[2.25rem] h-9 px-2 inline-flex items-center justify-center rounded-md text-sm border border-zinc-900 text-zinc-700'

  return (
    <nav className="flex items-center justify-center gap-1.5 mt-10 flex-wrap">
      {page > 1 ? (
        <Link href={buildHref(basePath, prevPage, extraQuery)} className={linkCls}>
          ← 이전
        </Link>
      ) : (
        <span className={disabledCls}>← 이전</span>
      )}
      {window.map((n, idx) => {
        const gap = idx > 0 && n - window[idx - 1] > 1
        return (
          <span key={n} className="contents">
            {gap && <span className="text-zinc-600 px-1">…</span>}
            {n === page ? (
              <span className={activeCls}>{n}</span>
            ) : (
              <Link href={buildHref(basePath, n, extraQuery)} className={linkCls}>
                {n}
              </Link>
            )}
          </span>
        )
      })}
      {page < totalPages ? (
        <Link href={buildHref(basePath, nextPage, extraQuery)} className={linkCls}>
          다음 →
        </Link>
      ) : (
        <span className={disabledCls}>다음 →</span>
      )}
    </nav>
  )
}

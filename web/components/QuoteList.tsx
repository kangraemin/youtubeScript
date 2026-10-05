import { Quote } from '@/lib/supabase'
import { youtubeJumpUrl } from '@/lib/timestamp'

// 근거 발언은 기본으로 접는다. 요약 1편에 인용이 평균 88개라 전부 펼치면
// 상세가 모바일 16화면까지 늘어났다(2026-10-05 실측, 접으면 약 10화면).
// 이탤릭은 쓰지 않는다 — 한글은 이탤릭 서체가 없어 기울임 합성이 되고, 상세 글자의 절반이 그 상태였다.
export function QuoteList({ vid, quotes }: { vid: string; quotes?: Quote[] }) {
  if (!quotes?.length) return null
  return (
    <details className="group mt-2">
      <summary className="cursor-pointer select-none list-none text-xs text-zinc-400 hover:text-zinc-200">
        <span className="group-open:hidden">▸ 근거 발언 {quotes.length}개</span>
        <span className="hidden group-open:inline">▾ 근거 발언 접기</span>
      </summary>
      <ul className="mt-2 space-y-2 border-l-2 border-zinc-700 pl-3">
        {quotes.map((q, i) => (
          <li key={i} className="text-sm text-zinc-300">
            <a
              href={youtubeJumpUrl(vid, q.timestamp)}
              target="_blank"
              rel="noreferrer"
              className="font-mono text-xs text-sky-300 hover:underline mr-2 bg-sky-400/10 px-1.5 py-0.5 rounded"
            >
              {q.timestamp}
            </a>
            <span>&ldquo;{q.text}&rdquo;</span>
          </li>
        ))}
      </ul>
    </details>
  )
}

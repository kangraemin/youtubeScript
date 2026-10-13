import type { ReactNode } from 'react'
import { splitSentences } from './text'

export function SentenceList({ text }: { text: string }) {
  return (
    <ul className="reader-sentences">
      {splitSentences(text).map((sentence, i) => (
        <li key={i}>
          <span aria-hidden="true" className="sentence-dot" />
          <span>{sentence}</span>
        </li>
      ))}
    </ul>
  )
}

export function ReadableText({
  text,
  limit = 220,
  className = '',
}: {
  text: string
  limit?: number
  className?: string
}) {
  if (text.length <= limit)
    return <p className={`readable-text ${className}`}>{text}</p>
  return (
    <details className={`readable-disclosure ${className}`}>
      <summary>
        <span className="reader-preview">{text.slice(0, limit)}…</span>
        <span className="readable-open">내용 접기</span>
        <span className="readable-closed">
          전체 읽기 <span aria-hidden="true">＋</span>
        </span>
      </summary>
      <SentenceList text={text} />
    </details>
  )
}

export function LimitedList({
  items,
  label,
  bullets = false,
  compact = false,
}: {
  items: ReactNode[]
  label: string
  bullets?: boolean
  compact?: boolean
}) {
  const list = (children: ReactNode[]) => (
    <ul
      className={
        compact
          ? 'reader-list reader-list-compact'
          : bullets
            ? 'reader-list reader-list-bullets'
            : 'reader-list'
      }
    >
      {children.map((item, i) => (
        <li key={i}>{item}</li>
      ))}
    </ul>
  )
  return (
    <>
      {list(items.slice(0, 5))}
      {items.length > 5 && (
        <details className="reader-more">
          <summary>
            <span className="more-closed">
              {items.length - 5}개 더 보기
              <span className="sr-only"> · {label}</span>
            </span>
            <span className="more-open">
              접기<span className="sr-only"> · {label}</span>
            </span>
            <span aria-hidden="true" className="disclosure-arrow">
              ⌄
            </span>
          </summary>
          {list(items.slice(5))}
        </details>
      )}
    </>
  )
}

export function SectionHeading({
  id,
  title,
  count,
  description,
}: {
  id: string
  title: string
  count?: number
  description?: string
}) {
  return (
    <div className="section-heading">
      <div>
        <h2 id={`${id}-heading`}>
          {title}
          {count != null && <span className="section-count">{count}</span>}
        </h2>
        {description && <p>{description}</p>}
      </div>
    </div>
  )
}

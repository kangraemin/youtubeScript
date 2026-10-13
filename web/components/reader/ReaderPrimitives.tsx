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
  className = '',
}: {
  text: string
  limit?: number
  className?: string
}) {
  return (
    <div className={`readable-text ${className}`}>
      <SentenceList text={text} />
    </div>
  )
}
export function LimitedList({
  items,
  compact = false,
}: {
  items: ReactNode[]
  label: string
  bullets?: boolean
  compact?: boolean
}) {
  return (
    <ul className={compact ? 'reader-list reader-list-compact' : 'reader-list'}>
      {items.map((item, i) => (
        <li key={i}>{item}</li>
      ))}
    </ul>
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

'use client'

import { useEffect, useState } from 'react'

export function ReaderNav({
  sections,
}: {
  sections: { id: string; title: string }[]
}) {
  const [current, setCurrent] = useState(sections[0]?.id)

  useEffect(() => {
    let frame = 0
    const update = () => {
      frame = 0
      let active = sections[0]?.id
      for (const { id } of sections) {
        const section = document.getElementById(id)
        if (section && section.getBoundingClientRect().top <= 112) active = id
      }
      setCurrent(active)
    }
    const schedule = () => {
      if (!frame) frame = requestAnimationFrame(update)
    }
    const initialTarget = document.getElementById(window.location.hash.slice(1))
    initialTarget?.scrollIntoView({ block: 'start' })
    update()
    window.addEventListener('scroll', schedule, { passive: true })
    window.addEventListener('resize', schedule)
    window.addEventListener('hashchange', schedule)
    return () => {
      cancelAnimationFrame(frame)
      window.removeEventListener('scroll', schedule)
      window.removeEventListener('resize', schedule)
      window.removeEventListener('hashchange', schedule)
    }
  }, [sections])

  return (
    <nav aria-label="요약 목차" className="reader-nav">
      <label className="reader-nav-select">
        <span>목차 · 바로 이동</span>
        <select
          aria-label="읽을 내용 선택"
          value={current}
          onChange={(event) => {
            window.location.hash = event.target.value
            document.getElementById(event.target.value)?.scrollIntoView({ block: 'start' })
            setCurrent(event.target.value)
          }}
        >
          {sections.map(({ id, title }) => (
            <option key={id} value={id}>
              {title}
            </option>
          ))}
        </select>
      </label>
      <div className="reader-nav-track">
        {sections.map(({ id, title }) => (
          <a
            key={id}
            href={`#${id}`}
            className="reader-jump"
            aria-current={current === id ? 'location' : undefined}
          >
            {title}
          </a>
        ))}
      </div>
    </nav>
  )
}

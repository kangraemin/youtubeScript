'use client'

import { useEffect, useRef, useState } from 'react'

export function ReaderNav({
  sections,
}: {
  sections: { id: string; title: string }[]
}) {
  const navRef = useRef<HTMLElement>(null)
  const [current, setCurrent] = useState(sections[0]?.id)

  useEffect(() => {
    let frame = 0
    const update = () => {
      frame = 0
      const offset = (navRef.current?.getBoundingClientRect().height ?? 60) + 16
      document.documentElement.style.setProperty('--reader-nav-offset', `${offset}px`)
      let active = sections[0]?.id
      for (const { id } of sections) {
        const section = document.getElementById(id)
        if (section && section.getBoundingClientRect().top <= offset + 8) active = id
      }
      setCurrent(active)
    }
    const schedule = () => {
      if (!frame) frame = requestAnimationFrame(update)
    }
    update()
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
    <nav ref={navRef} aria-label="요약 목차" className="reader-nav">
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

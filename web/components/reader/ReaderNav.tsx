'use client'

import { useEffect, useState } from 'react'

export function ReaderNav({ sections }: { sections: { id: string; title: string }[] }) {
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

  return <nav aria-label="요약 목차" className="sticky top-0 z-10 mb-8 min-w-0 border-y border-zinc-800 bg-bg/95 backdrop-blur">
    <div className="flex gap-1 overflow-x-auto py-2">
      {sections.map(({ id, title }) => <a key={id} href={`#${id}`} className="reader-jump"
        aria-current={current === id ? 'location' : undefined}>{title}</a>)}
    </div>
  </nav>
}

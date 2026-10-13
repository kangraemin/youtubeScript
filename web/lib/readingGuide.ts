export type ReadingGuide = {
  version: number
  title: string
  introduction: string
  topics: {
    id: string
    title: string
    ts: string
    speaker: string
    points: string[]
    background: string[]
    takeaways: string[]
    caveats?: string[]
  }[]
  perspectives: { name: string; view: string; watch: string }[]
  lessons: string[]
  sources: { label: string; url: string }[]
  coverage: {
    transcript_lines: number
    read_lines: number
    sha256?: string
    excluded: string
    note?: string
  }
}

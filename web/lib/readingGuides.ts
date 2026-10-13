import guide from '@/content/reading-guides/WtEo31SpSeI.json'
import aspimGuide from '@/content/reading-guides/xAFKbVXUkMA.json'
import type { ReadingGuide } from './readingGuide'
const guides: Record<string, ReadingGuide> = {
  WtEo31SpSeI: guide,
  xAFKbVXUkMA: aspimGuide,
}
export const getReadingGuide = (vid: string) => guides[vid]

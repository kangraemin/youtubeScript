// 소수점과 영문 약어 내부를 보존해야 수치·종목명이 달라지지 않는다.
export function splitSentences(text: string): string[] {
  return text.split(/(?<=[다음함임][.!?])\s*|(?<=[.!?])\s+|\n+/u)
    .map((sentence) => sentence.trim()).filter(Boolean)
}

export function splitHeadline(text: string): string[] {
  return text.split(/\s+[\/|]\s+|—/u).map((point) => point.trim()).filter(Boolean)
}

export function isHeadlineMeta(text: string, channel?: string): boolean {
  return text.length <= 10 && Boolean(channel?.trim() && text.includes(channel.trim()))
}

export function splitNarrative(text: string): string[] {
  return text.split(/\s*(?:→|⇒|➜|▶|▷|->|=>)\s*|\n+/u)
    .map((step) => step.trim()).filter(Boolean)
}

export function narrativeHeading(step: string): { time: string; title: string } {
  const match = step.match(/^\s*\[?\(?((?:\d{1,2}:)?\d{1,3}:\d{2}(?:\s*[-–—~〜]\s*(?:\d{1,2}:)?\d{1,3}:\d{2})?)\)?\]?\s*[:：-]?\s*/u)
  const body = match ? step.slice(match[0].length) : step
  return { time: match?.[1] ?? '', title: body || step }
}

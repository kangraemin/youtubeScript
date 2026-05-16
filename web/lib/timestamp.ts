/** "H:MM:SS" → 초로 변환. YouTube ?t= 파라미터용 */
export function timestampToSeconds(ts: string): number {
  const parts = ts.split(':').map(Number)
  if (parts.length === 3) return parts[0] * 3600 + parts[1] * 60 + parts[2]
  if (parts.length === 2) return parts[0] * 60 + parts[1]
  return parts[0] ?? 0
}

/** 영상 vid + 타임스탬프 → YouTube 점프 URL */
export function youtubeJumpUrl(vid: string, ts: string): string {
  return `https://www.youtube.com/watch?v=${vid}&t=${timestampToSeconds(ts)}s`
}

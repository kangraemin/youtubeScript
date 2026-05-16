// vid로부터 YouTube 썸네일/링크 URL 생성.

export function thumbnailUrl(vid: string, quality: 'mq' | 'hq' | 'maxres' = 'mq'): string {
  // mq=320x180 (가장 안정), hq=480x360, maxres=1280x720 (없을 수 있음)
  return `https://i.ytimg.com/vi/${vid}/${quality}default.jpg`
}

export function watchUrl(vid: string, seconds?: number): string {
  const base = `https://www.youtube.com/watch?v=${vid}`
  return seconds != null ? `${base}&t=${seconds}s` : base
}

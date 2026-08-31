// 주식·경제 채널 메타데이터 — 표시 이름과 색상.
// channel_slug별 노출용 라벨/색상. 새 채널 추가 시 여기만 갱신.

export type ChannelMeta = {
  slug: string
  name: string
  color: string // tailwind 텍스트 색상 클래스 prefix
  hex: string // 카드 보더/배지용
}

// 채널색은 카드가 나란히 놓였을 때 서로 구분되는 것이 목적이다.
// 예전엔 11개 중 5개가 hue 160~217°(청록~파랑)에 몰려 머니코믹스↔애스핌이 9.9°까지 붙었다.
// Tailwind 500 팔레트에서 최소 인접 간격이 가장 큰 11색 조합을 골라 재배치했다(최소 20.8°).
// 새 채널을 추가할 땐 아래 hue 주석을 보고 가장 넓은 빈 구간에서 고른다.
// 키 순서 = 홈 채널 그리드 표시 순서(STOCK_ECON_SLUGS가 Object.keys를 쓴다). 기존 순서를 유지한다.
// hue 주석은 색 배치 확인용 — 새 채널은 가장 넓은 빈 구간(예: 84~142°, 292~360°)에서 고른다.
export const CHANNEL_META: Record<string, ChannelMeta> = {
  shukaworld: { slug: 'shukaworld', name: '슈카월드', color: 'yellow', hex: '#eab308' }, // 45°
  moneycomics: { slug: 'moneycomics', name: '머니코믹스', color: 'sky', hex: '#0ea5e9' }, // 199°
  yonhap_economy: { slug: 'yonhap_economy', name: '연합경제TV', color: 'red', hex: '#ef4444' }, // 0°
  jisik_inside: { slug: 'jisik_inside', name: '지식인사이드', color: 'purple', hex: '#a855f7' }, // 271°
  developmong: { slug: 'developmong', name: '디벨롭몽', color: 'green', hex: '#22c55e' }, // 142°
  doniggangpae: { slug: 'doniggangpae', name: '돈깡패', color: 'orange', hex: '#f97316' }, // 25°
  mk_wallstreet: { slug: 'mk_wallstreet', name: '매경 월가월부', color: 'indigo', hex: '#6366f1' }, // 239°
  sbs_gyoyangi: { slug: 'sbs_gyoyangi', name: '교양이를 부탁해', color: 'teal', hex: '#14b8a6' }, // 173°
  aspim_research: { slug: 'aspim_research', name: '애스핌 리서치', color: 'pink', hex: '#ec4899' }, // 330°
  alsangmoo: { slug: 'alsangmoo', name: '알상무', color: 'fuchsia', hex: '#d946ef' }, // 292°
  wepoll: { slug: 'wepoll', name: '위폴', color: 'lime', hex: '#84cc16' }, // 84°
}

export const STOCK_ECON_SLUGS = Object.keys(CHANNEL_META)

export function getChannelMeta(slug: string, fallbackName?: string): ChannelMeta {
  return (
    CHANNEL_META[slug] ?? {
      slug,
      name: fallbackName ?? slug,
      color: 'zinc',
      hex: '#71717a',
    }
  )
}

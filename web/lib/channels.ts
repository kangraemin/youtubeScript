// 주식·경제 채널 메타데이터 — 표시 이름과 색상.
// channel_slug별 노출용 라벨/색상. 새 채널 추가 시 여기만 갱신.

export type ChannelMeta = {
  slug: string
  name: string
  color: string // tailwind 텍스트 색상 클래스 prefix
  hex: string // 카드 보더/배지용
}

export const CHANNEL_META: Record<string, ChannelMeta> = {
  shukaworld: { slug: 'shukaworld', name: '슈카월드', color: 'amber', hex: '#f59e0b' },
  moneycomics: { slug: 'moneycomics', name: '머니코믹스', color: 'sky', hex: '#0ea5e9' },
  yonhap_economy: { slug: 'yonhap_economy', name: '연합경제TV', color: 'rose', hex: '#f43f5e' },
  jisik_inside: { slug: 'jisik_inside', name: '지식인사이드', color: 'violet', hex: '#8b5cf6' },
  developmong: { slug: 'developmong', name: '디벨롭몽', color: 'emerald', hex: '#10b981' },
  doniggangpae: { slug: 'doniggangpae', name: '돈깡패', color: 'orange', hex: '#f97316' },
  mk_wallstreet: { slug: 'mk_wallstreet', name: '매경 월가월부', color: 'blue', hex: '#3b82f6' },
  sbs_gyoyangi: { slug: 'sbs_gyoyangi', name: '교양이를 부탁해', color: 'teal', hex: '#14b8a6' },
  aspim_research: { slug: 'aspim_research', name: '애스핌 리서치', color: 'cyan', hex: '#06b6d4' },
  // 기존 채널이 hue 160~260°(청록~보라)에 몰려 있어, 신규 2개는 비어 있던 구간에서 고른다.
  // indigo(#6366f1)는 지식인사이드(258°)·매경(217°)과 20° 안쪽이라 카드가 나란히 놓이면 구분이 안 된다.
  alsangmoo: { slug: 'alsangmoo', name: '알상무', color: 'fuchsia', hex: '#d946ef' }, // ~292°
  wepoll: { slug: 'wepoll', name: '위폴', color: 'lime', hex: '#84cc16' }, // ~84°
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

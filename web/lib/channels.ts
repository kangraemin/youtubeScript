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
  moneycomics_videos: {
    slug: 'moneycomics_videos',
    name: '머니코믹스 클립',
    color: 'cyan',
    hex: '#06b6d4',
  },
  yonhap_economy: { slug: 'yonhap_economy', name: '연합경제TV', color: 'rose', hex: '#f43f5e' },
  jisik_inside: { slug: 'jisik_inside', name: '지식인사이드', color: 'violet', hex: '#8b5cf6' },
  developmong: { slug: 'developmong', name: '디벨롭몽', color: 'emerald', hex: '#10b981' },
  doniggangpae: { slug: 'doniggangpae', name: '돈깡패', color: 'orange', hex: '#f97316' },
  mk_wallstreet: { slug: 'mk_wallstreet', name: '매경 월가월부', color: 'blue', hex: '#3b82f6' },
  sbs_gyoyangi: { slug: 'sbs_gyoyangi', name: '교양이를 부탁해', color: 'teal', hex: '#14b8a6' },
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

# youtube-script-web

YouTube 주식·경제 transcript 요약 웹 (Next.js 15 App Router + Supabase + Tailwind).

## 로컬 개발

```bash
cd web
npm install
# .env.local 에 NEXT_PUBLIC_SUPABASE_URL / NEXT_PUBLIC_SUPABASE_ANON_KEY 가 있어야 함 (상위 .env.local에서 자동 복사 가능)
npm run dev
# http://localhost:3000
```

## 라우트
- `/` — 홈, 최신 요약 20편
- `/channel/[slug]` — 채널별 영상 목록 (50편)
- `/video/[vid]` — 상세, SummaryCard + 원본 transcript 토글

## Cloudflare Workers 배포 (OpenNext)

Vercel 계정이 2026-10-28부터 402로 막혀 2026-10-29 Cloudflare로 옮김.

```bash
export PATH=/opt/homebrew/opt/node@22/bin:$PATH; unset CLOUDFLARE_API_TOKEN
npx opennextjs-cloudflare build && npx wrangler deploy
npx wrangler secret put REVALIDATE_SECRET   # /api/revalidate 용
```

- **주소**: https://youtube-summary.remin1994.workers.dev
- 설정: `wrangler.jsonc`, `open-next.config.ts` (ISR 캐시 없음, 요청마다 렌더)
- `NEXT_PUBLIC_SUPABASE_*`는 빌드 시 `.env.local`에서 들어감

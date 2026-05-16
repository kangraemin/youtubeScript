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

## Vercel 배포

### 1) Vercel CLI로 preview 배포 (가장 빠른 방법)

```bash
cd web
npx vercel
```

대화형 프롬프트에 답:
- `Set up and deploy "~/web"?` → Y
- `Which scope?` → 사용자 계정 선택
- `Link to existing project?` → N (첫 배포)
- `What's your project's name?` → `youtube-script` 같은 이름
- `In which directory is your code located?` → `./` (현재 디렉토리)

빌드 후 preview URL 출력됨. 예: `https://youtube-script-abc.vercel.app`

### 2) 환경변수 등록 (필수)

Vercel CLI가 첫 배포 시 자동 감지하기도 하지만, 안 잡히면 dashboard에서 수동 등록:

```
NEXT_PUBLIC_SUPABASE_URL = <상위 .env.local 값>
NEXT_PUBLIC_SUPABASE_ANON_KEY = <상위 .env.local 값>
```

(Environments: Production, Preview, Development 모두 체크)

### 3) Production promote

preview에서 동작 확인 후 dashboard에서 Promote to Production. 또는:

```bash
npx vercel --prod
```

### 4) 기존 GitHub Pages

`gh-pages` 브랜치는 그대로 유지 (롤백 대비). Vercel preview에서 안정 확인 후 사용자 판단으로 정리.

## 배포 결과

- **Production**: https://web-3j1j6acqj-remin1994-3460s-projects.vercel.app
- **별칭**: https://web-green-kappa-79.vercel.app
- 배포 시각: 2026-05-16
- Region: 자동 (Vercel 기본)
- Env vars: `NEXT_PUBLIC_SUPABASE_URL`, `NEXT_PUBLIC_SUPABASE_ANON_KEY` (Production + Development 등록 완료)

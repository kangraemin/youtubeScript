import { NextRequest, NextResponse } from 'next/server'
import { revalidatePath } from 'next/cache'

// 새 요약 저장 시 save_summary.py가 호출 → 홈/latest 캐시 즉시 무효화.
// 미설정/토큰 불일치는 401 (무인 cron 노출 보호).
export async function POST(req: NextRequest) {
  const secret = req.nextUrl.searchParams.get('secret')
  if (!process.env.REVALIDATE_SECRET || secret !== process.env.REVALIDATE_SECRET) {
    return NextResponse.json({ ok: false, error: 'unauthorized' }, { status: 401 })
  }
  revalidatePath('/')
  revalidatePath('/latest')
  return NextResponse.json({ ok: true, revalidated: ['/', '/latest'], at: Date.now() })
}

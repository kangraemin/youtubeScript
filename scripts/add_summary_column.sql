-- transcripts 테이블에 summary 컬럼 추가
-- Supabase SQL Editor에서 1회 실행 (멱등 — ADD COLUMN IF NOT EXISTS)

ALTER TABLE public.transcripts
  ADD COLUMN IF NOT EXISTS summary JSONB,
  ADD COLUMN IF NOT EXISTS summarized_at TIMESTAMPTZ,
  ADD COLUMN IF NOT EXISTS summary_model TEXT;

-- 요약된 row만 빠르게 조회 (ORDER BY summarized_at DESC 용)
CREATE INDEX IF NOT EXISTS transcripts_summarized_idx
  ON public.transcripts (summarized_at)
  WHERE summarized_at IS NOT NULL;

-- 미요약 대기열 빠르게 SELECT (채널 필터 + published_at 정렬)
CREATE INDEX IF NOT EXISTS transcripts_summary_pending_idx
  ON public.transcripts (channel_slug, published_at DESC)
  WHERE summary IS NULL AND transcript IS NOT NULL;

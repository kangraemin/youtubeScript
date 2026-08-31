-- 홈 채널 카드용 집계 RPC.
-- 기존 홈은 summary 있는 행의 (channel_slug, published_at)을 1000개씩 페이지네이션으로
-- 전부 끌어와 JS에서 집계했다 — 요약이 1,075건일 때 1,075행 전송 + 1.5초.
-- 요약이 늘수록 선형으로 느려지므로 DB에서 집계해 채널 수만큼(현재 11행)만 반환한다.

drop function if exists public.channel_stats();

create function public.channel_stats()
returns table (
  channel_slug text,
  count_summarized bigint,
  latest_published_at date
)
language sql
stable
as $$
  select t.channel_slug,
         count(*) as count_summarized,
         max(t.published_at) as latest_published_at
  from public.transcripts t
  where t.summary is not null
  group by t.channel_slug
$$;

grant execute on function public.channel_stats() to anon, authenticated;

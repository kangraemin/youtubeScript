-- 브라우즈 피드용 경량 RPC.
-- 피드 카드(VideoCard)는 headline + 매수/매도/관전/용어 "개수"만 쓰는데
-- 기존 피드는 summary(13섹션 전체 jsonb)를 통째로 끌어와 페이로드가 컸다.
-- 여기서 headline + jsonb_array_length 카운트만 반환해 페이로드를 대폭 줄인다.
-- (검색은 search_transcripts RPC가 matchReason용으로 summary 본문을 그대로 반환)

drop function if exists public.feed_summaries(text, int, int);

create function public.feed_summaries(
  p_channel text default null,
  p_limit int default 20,
  p_offset int default 0
)
returns table (
  vid text,
  channel text,
  channel_slug text,
  title text,
  published_at date,
  summarized_at timestamptz,
  headline text,
  n_buys int,
  n_sells int,
  n_watch int,
  n_terms int
)
language sql
stable
as $$
  select t.vid, t.channel, t.channel_slug, t.title, t.published_at, t.summarized_at,
         t.summary->>'headline' as headline,
         coalesce(jsonb_array_length(t.summary->'buys'), 0) as n_buys,
         coalesce(jsonb_array_length(t.summary->'sells'), 0) as n_sells,
         coalesce(jsonb_array_length(t.summary->'watchlist'), 0) as n_watch,
         coalesce(jsonb_array_length(t.summary->'terms'), 0) as n_terms
  from public.transcripts t
  where t.summary is not null
    and (p_channel is null or t.channel_slug = p_channel)
  order by t.published_at desc nulls last
  limit p_limit offset p_offset
$$;

grant execute on function public.feed_summaries(text, int, int) to anon, authenticated;

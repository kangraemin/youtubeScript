-- 브라우즈 피드용 경량 RPC.
-- 피드 카드(VideoCard)는 headline + 매수/매도/관전/용어 "개수"만 쓰는데
-- 기존 피드는 summary(13섹션 전체 jsonb)를 통째로 끌어와 페이로드가 컸다.
-- 여기서 headline + jsonb_array_length 카운트만 반환해 페이로드를 대폭 줄인다.
-- (검색은 search_transcripts RPC가 matchReason용으로 summary 본문을 그대로 반환)
--
-- p_min_duration: 웹 "쇼츠 숨기기" 필터. 이 값 이상인 영상만 반환한다(0이면 전체).
--   duration_sec IS NULL(아직 백필 안 된 행)과 -1(삭제·비공개로 조회 불가)은
--   길이를 알 수 없으므로 필터가 켜져 있으면 제외한다.

drop function if exists public.feed_summaries(text, int, int);
drop function if exists public.feed_summaries(text, int, int, int);

create function public.feed_summaries(
  p_channel text default null,
  p_limit int default 20,
  p_offset int default 0,
  p_min_duration int default 0
)
returns table (
  vid text,
  channel text,
  channel_slug text,
  title text,
  published_at date,
  summarized_at timestamptz,
  duration_sec int,
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
         t.duration_sec,
         t.summary->>'headline' as headline,
         coalesce(jsonb_array_length(t.summary->'buys'), 0) as n_buys,
         coalesce(jsonb_array_length(t.summary->'sells'), 0) as n_sells,
         coalesce(jsonb_array_length(t.summary->'watchlist'), 0) as n_watch,
         coalesce(jsonb_array_length(t.summary->'terms'), 0) as n_terms
  from public.transcripts t
  where t.summary is not null
    and (p_channel is null or t.channel_slug = p_channel)
    and (p_min_duration <= 0 or t.duration_sec >= p_min_duration)
  order by t.published_at desc nulls last
  limit p_limit offset p_offset
$$;

grant execute on function public.feed_summaries(text, int, int, int) to anon, authenticated;

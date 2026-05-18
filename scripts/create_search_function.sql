-- pg_trgm: ILIKE '%...%' substring 매칭을 GIN 인덱스로 가속.
-- 없으면 summary::text 풀스캔이 컴퓨트를 포화시켜 검색 1회에 522 발생.
create extension if not exists pg_trgm;

create index if not exists idx_transcripts_title_trgm
  on public.transcripts using gin (title gin_trgm_ops);

create index if not exists idx_transcripts_summary_trgm
  on public.transcripts using gin ((summary::text) gin_trgm_ops);

-- 갓 생성된 GIN 인덱스는 통계가 없어 플래너가 seqscan → statement timeout.
-- ANALYZE로 통계 갱신해야 trgm 인덱스를 실제로 사용한다.
analyze public.transcripts;

-- returns table(7컬럼): setof transcripts는 select 무관 전 컬럼 반환(거대 transcript 포함)이라
-- DB가 wide row를 스캔·정렬. 필요한 7컬럼만 반환해 IO/정렬 비용 절감.
-- 반환타입 변경은 create or replace 불가 → drop 먼저.
drop function if exists public.search_transcripts(text);

create function public.search_transcripts(q_input text)
returns table (
  vid text,
  channel text,
  channel_slug text,
  title text,
  published_at date,
  summary jsonb,
  summarized_at timestamptz
)
language sql
stable
as $$
  select t.vid, t.channel, t.channel_slug, t.title,
         t.published_at, t.summary, t.summarized_at
  from public.transcripts t
  where t.summary is not null
    and (
      t.title ilike '%' || q_input || '%'
      or t.summary::text ilike '%' || q_input || '%'
    )
  order by t.published_at desc nulls last
$$;

grant execute on function public.search_transcripts(text) to anon, authenticated;

-- PostgREST 스키마 캐시 리로드 (신규 함수 즉시 노출)
notify pgrst, 'reload schema';

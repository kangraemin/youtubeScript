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

create or replace function public.search_transcripts(q_input text)
returns setof public.transcripts
language sql
stable
as $$
  select *
  from public.transcripts
  where summary is not null
    and (
      title ilike '%' || q_input || '%'
      or summary::text ilike '%' || q_input || '%'
    )
  order by published_at desc nulls last
$$;

grant execute on function public.search_transcripts(text) to anon, authenticated;

-- PostgREST 스키마 캐시 리로드 (신규 함수 즉시 노출)
notify pgrst, 'reload schema';

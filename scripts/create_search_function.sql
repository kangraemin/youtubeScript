-- pg_trgm: ILIKE '%...%' substring 매칭을 GIN 인덱스로 가속.
-- 없으면 summary::text 풀스캔이 컴퓨트를 포화시켜 검색 1회에 522 발생.
create extension if not exists pg_trgm;

create index if not exists idx_transcripts_title_trgm
  on public.transcripts using gin (title gin_trgm_ops);

create index if not exists idx_transcripts_summary_trgm
  on public.transcripts using gin ((summary::text) gin_trgm_ops);

-- ANALYZE로 통계 갱신해야 trgm 인덱스를 실제로 사용한다.
analyze public.transcripts;

-- 검색 RPC.
-- p_limit/p_offset이 없던 시절엔 매칭되는 행을 전부 반환했다. '삼성전자' 검색 시 440행이
-- 걸리는데 각 행의 summary가 평균 10KB(최대 77KB)라 4MB 넘는 결과를 만들어 보냈다.
-- 웹은 그중 20개만 그린다. 서버에서 잘라 전송량을 20배 이상 줄인다.
--
-- summary 본문은 필요하다 — 웹의 matchReason이 buys/sells/watchlist/terms/narrative를 훑어
-- 매칭 근거 스니펫을 만들기 때문에 헤드라인만으로는 대체할 수 없다.
-- 다만 quotes(발화 원문)는 matchReason이 전혀 보지 않으면서 payload의 57%를 차지한다.
-- strip_quotes로 떼고 보낸다. 상세 페이지는 이 RPC를 쓰지 않으니 인용문 표시에 영향 없다.

-- 각 섹션 배열 요소에서 quotes 키만 제거. 나머지 구조는 그대로 둔다.
create or replace function public.strip_quotes(s jsonb)
returns jsonb language sql immutable as $fn$
  select coalesce(jsonb_object_agg(kv.key,
    case when jsonb_typeof(kv.value) = 'array' then (
      select coalesce(jsonb_agg(
        case when jsonb_typeof(e) = 'object' then e - 'quotes' else e end
      ), '[]'::jsonb)
      from jsonb_array_elements(kv.value) e
    ) else kv.value end
  ), '{}'::jsonb)
  from jsonb_each(s) kv
$fn$;

grant execute on function public.strip_quotes(jsonb) to anon, authenticated;

drop function if exists public.search_transcripts(text);
drop function if exists public.search_transcripts(text, int, int);

create function public.search_transcripts(
  q_input text,
  p_limit int default 20,
  p_offset int default 0
)
returns table (
  vid text,
  channel text,
  channel_slug text,
  title text,
  published_at date,
  summary jsonb,
  summarized_at timestamptz,
  duration_sec int
)
language sql
stable
as $$
  select t.vid, t.channel, t.channel_slug, t.title,
         t.published_at, public.strip_quotes(t.summary) as summary,
         t.summarized_at, t.duration_sec
  from public.transcripts t
  where t.summary is not null
    and (
      t.title ilike '%' || q_input || '%'
      or t.summary::text ilike '%' || q_input || '%'
    )
  order by t.published_at desc nulls last
  limit p_limit offset p_offset
$$;

grant execute on function public.search_transcripts(text, int, int) to anon, authenticated;

-- PostgREST 스키마 캐시 리로드 (신규 함수 즉시 노출)
notify pgrst, 'reload schema';

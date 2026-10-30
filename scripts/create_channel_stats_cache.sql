-- 홈 채널 집계를 미리 쌓아 둔 표에서 읽는다(10/31: transcripts 집계가 DB IO 부족으로 4~10초 → anon 타임아웃·홈 500).
create table if not exists public.channel_stats_cache (
  channel_slug text primary key,
  count_summarized bigint not null default 0,
  latest_published_at date
);
alter table public.channel_stats_cache enable row level security;

create or replace function public.channel_stats_cache_bump() returns trigger
language plpgsql security definer set search_path = public as $$
declare
  was boolean := tg_op in ('UPDATE','DELETE') and old.summary is not null;
  now_ boolean := tg_op in ('INSERT','UPDATE') and new.summary is not null;
begin
  if was and (not now_ or new.channel_slug is distinct from old.channel_slug) then
    update channel_stats_cache set count_summarized = count_summarized - 1 where channel_slug = old.channel_slug;
  end if;
  if now_ and (not was or new.channel_slug is distinct from old.channel_slug) then
    insert into channel_stats_cache as c values (new.channel_slug, 1, new.published_at)
    on conflict (channel_slug) do update
      set count_summarized = c.count_summarized + 1,
          latest_published_at = greatest(c.latest_published_at, excluded.latest_published_at);
  elsif now_ then
    update channel_stats_cache set latest_published_at = greatest(latest_published_at, new.published_at)
    where channel_slug = new.channel_slug and new.published_at is distinct from old.published_at;
  end if;
  return null;
end $$;

drop trigger if exists transcripts_channel_stats_cache on public.transcripts;
create trigger transcripts_channel_stats_cache
after insert or delete or update of summary, channel_slug, published_at on public.transcripts
for each row execute function public.channel_stats_cache_bump();

insert into public.channel_stats_cache
select channel_slug, count(*), max(published_at) from public.transcripts
where summary is not null group by channel_slug
on conflict (channel_slug) do update
  set count_summarized = excluded.count_summarized, latest_published_at = excluded.latest_published_at;

create or replace function public.channel_stats()
 returns table(channel_slug text, count_summarized bigint, latest_published_at date)
 language sql stable security definer set search_path = public
as $$ select channel_slug, count_summarized, latest_published_at from channel_stats_cache $$;

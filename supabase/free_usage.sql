-- PhotoCleaner: Free usage quota tracking (Supabase)

create table if not exists public.free_usage (
  device_id text primary key,
  total_used integer not null default 0,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create or replace function public.consume_free_images(
  p_device_id text,
  p_amount integer
)
returns table (
  allowed boolean,
  remaining integer,
  used_total integer
)
language plpgsql
security definer
set search_path = public
as $$
declare
  current_total integer;
  new_total integer;
  limit_total integer := 250;
begin
  if p_device_id is null or length(p_device_id) = 0 then
    raise exception 'device_id required';
  end if;

  if p_amount is null or p_amount <= 0 then
    select total_used into current_total
    from public.free_usage
    where device_id = p_device_id;

    if current_total is null then
      current_total := 0;
    end if;

    return query select true, greatest(limit_total - current_total, 0), current_total;
    return;
  end if;

  insert into public.free_usage (device_id, total_used)
  values (p_device_id, 0)
  on conflict (device_id) do nothing;

  select total_used into current_total
  from public.free_usage
  where device_id = p_device_id
  for update;

  if current_total is null then
    current_total := 0;
  end if;

  new_total := current_total + p_amount;

  if new_total > limit_total then
    return query select false, greatest(limit_total - current_total, 0), current_total;
    return;
  end if;

  update public.free_usage
  set total_used = new_total,
      updated_at = now()
  where device_id = p_device_id;

  return query select true, limit_total - new_total, new_total;
end;
$$;

alter table public.free_usage enable row level security;

do $$
begin
  if not exists (
    select 1 from pg_policies
    where schemaname = 'public' and tablename = 'free_usage' and policyname = 'no_direct_access'
  ) then
    create policy no_direct_access
      on public.free_usage
      for all
      using (false);
  end if;
end $$;

grant execute on function public.consume_free_images(text, integer) to anon, authenticated;

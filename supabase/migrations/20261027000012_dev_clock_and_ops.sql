-- Dev mode and operations (milestones 06/09).
--
-- 1. Dev clock: a local database can run on a simulated time, for every session (the app
--    included), so a whole campaign can be played in minutes (`python -m jobs.dev`).
--    The row lives in the private schema, writable only by the database owner; production
--    never has a row, so private.clock() is the real time there. A direct session's
--    app.fake_now (tests, replay) still takes precedence.
-- 2. server_time(): the clock the RPCs use, for countdowns that do not trust the device.
-- 3. Tick journal: one row per tick (private), and a public one-row status for the app.

create table private.dev_clock (
  id boolean primary key default true check (id),
  fake_now timestamptz not null,
  -- true: time flows from fake_now since set_at; false: frozen at fake_now.
  running boolean not null default false,
  set_at timestamptz not null default now()
);

create or replace function private.clock()
returns timestamptz
language plpgsql
stable
security definer
set search_path = ''
as $$
declare
  v_fake text := nullif(current_setting('app.fake_now', true), '');
  v_dev private.dev_clock;
begin
  if v_fake is not null
     and session_user not in ('authenticator', 'anon', 'authenticated', 'service_role') then
    return v_fake::timestamptz;
  end if;
  select * into v_dev from private.dev_clock d where d.id;
  if found then
    return case when v_dev.running then v_dev.fake_now + (now() - v_dev.set_at)
                else v_dev.fake_now end;
  end if;
  return now();
end;
$$;

create function public.server_time()
returns timestamptz
language sql
stable
security definer
set search_path = ''
as $$ select private.clock() $$;

revoke execute on function public.server_time() from public, anon;
grant execute on function public.server_time() to authenticated;

-- Tick journal (jobs/tick.py): what ran, what waited, what failed, with its log lines.
create table private.tick_runs (
  id bigint generated always as identity primary key,
  started_at timestamptz not null default now(),
  finished_at timestamptz,
  game_time timestamptz not null,
  ok boolean,
  done jsonb not null default '[]'::jsonb,
  log jsonb not null default '[]'::jsonb,
  error text
);
create index tick_runs_started_idx on private.tick_runs (started_at desc);

-- One row, written by the jobs, read by the app's status page.
create table public.system_status (
  id boolean primary key default true check (id),
  last_tick_at timestamptz,
  last_tick_ok boolean,
  last_success_at timestamptz,
  consecutive_failures integer not null default 0,
  prices_updated_at timestamptz,
  dev_clock boolean not null default false,
  updated_at timestamptz not null default now()
);
alter table public.system_status enable row level security;
revoke all on public.system_status from anon, authenticated;
grant select on public.system_status to authenticated;
grant all on public.system_status to service_role;
create policy "authenticated read" on public.system_status
  for select to authenticated using (true);

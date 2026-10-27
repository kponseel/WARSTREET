-- Core tables: profiles, leagues, members, catalogue, prices, weeks, job bookkeeping.
-- Data model: docs/ARCHITECTURE.md §4. Players are league members (member_id); the Drone is
-- a member without a user account.

create table public.profiles (
  id uuid primary key references auth.users (id) on delete cascade,
  locale public.locale not null default 'en',
  created_at timestamptz not null default now()
);

-- A profile is created for every new auth user.
create function private.handle_new_user()
returns trigger
language plpgsql
security definer
set search_path = ''
as $$
begin
  insert into public.profiles (id) values (new.id) on conflict (id) do nothing;
  return new;
end;
$$;

create trigger on_auth_user_created
  after insert on auth.users
  for each row execute function private.handle_new_user();

create table public.leagues (
  id uuid primary key default gen_random_uuid(),
  name text not null,
  invite_code text not null unique,
  host_id uuid not null references auth.users (id) on delete restrict,
  status public.league_status not null default 'lobby',
  max_players integer not null,
  campaign_weeks integer not null,
  drone_enabled boolean not null default true,
  start_week date,
  created_at timestamptz not null default now(),
  started_at timestamptz,
  constraint start_week_is_monday check (start_week is null or extract(isodow from start_week) = 1)
);

create table public.league_members (
  member_id uuid primary key default gen_random_uuid(),
  league_id uuid not null references public.leagues (id) on delete cascade,
  user_id uuid references auth.users (id) on delete cascade,
  pseudo text not null,
  commander public.commander,
  avatar_color text not null,
  ready boolean not null default false,
  is_drone boolean not null default false,
  joined_at timestamptz not null default now(),
  constraint drone_has_no_user check (is_drone = (user_id is null)),
  constraint human_has_commander check (is_drone or commander is not null),
  unique (league_id, user_id)
);
create unique index league_members_pseudo_key on public.league_members (league_id, lower(pseudo));
create index league_members_user_idx on public.league_members (user_id);

create table public.instruments (
  id integer generated always as identity primary key,
  ticker text not null unique,
  name text not null,
  region public.region not null,
  calendar_mic text not null,
  currency text not null,
  sector text not null
);

-- Global market data, the same for every league.
create table public.instrument_weeks (
  instrument_id integer not null references public.instruments (id) on delete cascade,
  week date not null,
  vol12w numeric,
  coef numeric,
  display_class text,
  prev_week_return numeric,
  max_abs_daily_move_prev numeric,
  market_cap numeric,
  earnings_date date,
  in_conflict_zone boolean not null default false,
  weather text[] not null default '{}',
  primary key (instrument_id, week)
);
create index instrument_weeks_zone_idx on public.instrument_weeks (week) where in_conflict_zone;

create table public.reference_prices (
  instrument_id integer not null references public.instruments (id) on delete cascade,
  week date not null,
  kind public.price_kind not null,
  price numeric not null,
  dividend numeric not null default 0,
  split_ratio numeric not null default 1,
  source text not null,
  fetched_at timestamptz not null default now(),
  confirmed boolean not null default false,
  primary key (instrument_id, week, kind)
);

create table public.prices_live (
  instrument_id integer not null references public.instruments (id) on delete cascade,
  ts timestamptz not null,
  price numeric not null,
  primary key (instrument_id, ts)
);

-- One row per league week. Phase timestamps are UTC (GAME_RULES §2). lock_at and
-- resupply_closes_at depend only on the Paris clock; resupply_opens_at and debrief_at need
-- the XNYS calendar and are filled by the jobs.
create table public.weeks (
  league_id uuid not null references public.leagues (id) on delete cascade,
  week date not null,
  number integer not null,
  phase public.phase not null default 'briefing',
  is_final boolean not null default false,
  lock_at timestamptz not null,
  resupply_opens_at timestamptz,
  resupply_closes_at timestamptz not null,
  debrief_at timestamptz,
  phase_changed_at timestamptz not null default now(),
  primary key (league_id, week),
  unique (league_id, number),
  constraint week_is_monday check (extract(isodow from week) = 1)
);

-- Idempotence of global market transitions.
create table public.market_runs (
  week date not null,
  transition text not null,
  ran_at timestamptz not null default now(),
  primary key (week, transition)
);

-- Idempotence of league transitions.
create table public.job_runs (
  league_id uuid not null references public.leagues (id) on delete cascade,
  week date not null,
  transition text not null,
  ran_at timestamptz not null default now(),
  primary key (league_id, week, transition)
);

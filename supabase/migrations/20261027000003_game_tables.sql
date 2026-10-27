-- Game tables, all keyed by league member (docs/ARCHITECTURE.md §4).

create table public.squads (
  league_id uuid not null,
  week date not null,
  member_id uuid not null references public.league_members (member_id) on delete cascade,
  locked boolean not null default false,
  auto boolean not null default false,
  submitted_at timestamptz,
  primary key (league_id, week, member_id),
  foreign key (league_id, week) references public.weeks (league_id, week) on delete cascade
);

create table public.squad_units (
  league_id uuid not null,
  week date not null,
  member_id uuid not null,
  slot public.slot not null,
  instrument_id integer not null references public.instruments (id),
  active_s1 boolean not null default false,
  active_s2 boolean not null default false,
  primary key (league_id, week, member_id, slot),
  unique (league_id, week, member_id, instrument_id),
  foreign key (league_id, week, member_id)
    references public.squads (league_id, week, member_id) on delete cascade
);

-- Pending swaps; applied by the job at resupply_closes_at.
create table public.swaps (
  id uuid primary key default gen_random_uuid(),
  league_id uuid not null,
  week date not null,
  member_id uuid not null,
  slot public.slot not null,
  reserve_slot public.slot not null,
  created_at timestamptz not null default now(),
  unique (league_id, week, member_id, slot),
  unique (league_id, week, member_id, reserve_slot),
  foreign key (league_id, week, member_id)
    references public.squads (league_id, week, member_id) on delete cascade
);

create table public.ammo_ledger (
  id bigint generated always as identity primary key,
  league_id uuid not null references public.leagues (id) on delete cascade,
  member_id uuid not null references public.league_members (member_id) on delete cascade,
  week date,
  delta integer not null,
  reason text not null,
  order_id uuid,
  created_at timestamptz not null default now()
);
create index ammo_ledger_member_idx on public.ammo_ledger (member_id);

create table public.orders (
  id uuid primary key default gen_random_uuid(),
  league_id uuid not null,
  week date not null,
  member_id uuid not null references public.league_members (member_id) on delete cascade,
  type public.order_type not null,
  target_member_id uuid references public.league_members (member_id) on delete cascade,
  target_slot public.slot,
  order_window public.order_window not null,
  cost integer not null,
  status public.order_status not null default 'pending',
  created_at timestamptz not null,
  resolved_at timestamptz,
  foreign key (league_id, week) references public.weeks (league_id, week) on delete cascade
);
create index orders_week_idx on public.orders (league_id, week);
create index orders_target_idx on public.orders (target_member_id, week);

create table public.pacts (
  id uuid primary key default gen_random_uuid(),
  league_id uuid not null,
  week date not null,
  proposer_member_id uuid not null references public.league_members (member_id) on delete cascade,
  partner_member_id uuid not null references public.league_members (member_id) on delete cascade,
  status public.pact_status not null default 'proposed',
  created_at timestamptz not null,
  responded_at timestamptz,
  constraint pact_not_self check (proposer_member_id <> partner_member_id),
  foreign key (league_id, week) references public.weeks (league_id, week) on delete cascade
);
create index pacts_week_idx on public.pacts (league_id, week);

-- Private live score: owner only (and not while jammed). Written by the job.
create table public.scores_live (
  league_id uuid not null,
  week date not null,
  member_id uuid not null references public.league_members (member_id) on delete cascade,
  pf_live numeric,
  units jsonb not null default '{}'::jsonb,
  updated_at timestamptz not null default now(),
  primary key (league_id, week, member_id),
  foreign key (league_id, week) references public.weeks (league_id, week) on delete cascade
);

-- Public live score, written ALREADY MASKED by the job: no Shadow row, jammed rows without
-- PF, rank or per-unit PF. Clients subscribe to this table with Realtime.
create table public.scores_live_public (
  league_id uuid not null,
  week date not null,
  member_id uuid not null references public.league_members (member_id) on delete cascade,
  pf_live numeric,
  rank_live integer,
  jammed boolean not null default false,
  units jsonb not null default '{}'::jsonb,
  updated_at timestamptz not null default now(),
  primary key (league_id, week, member_id),
  foreign key (league_id, week) references public.weeks (league_id, week) on delete cascade
);

create table public.scores_final (
  league_id uuid not null,
  week date not null,
  member_id uuid not null references public.league_members (member_id) on delete cascade,
  pf_total integer not null,
  pf_picking integer not null,
  breakdown jsonb not null default '{}'::jsonb,
  rank integer,
  campaign_points numeric not null default 0,
  primary key (league_id, week, member_id),
  foreign key (league_id, week) references public.weeks (league_id, week) on delete cascade
);

create table public.badges (
  league_id uuid not null,
  week date not null,
  member_id uuid not null references public.league_members (member_id) on delete cascade,
  code text not null,
  primary key (league_id, week, member_id, code),
  foreign key (league_id, week) references public.weeks (league_id, week) on delete cascade
);

-- Server messages as template key + variables, rendered client-side in the reader's
-- language. audience_member_id null = every member of the league.
create table public.events (
  id bigint generated always as identity primary key,
  league_id uuid not null references public.leagues (id) on delete cascade,
  week date,
  ts timestamptz not null default now(),
  kind text not null,
  template_key text not null,
  vars jsonb not null default '{}'::jsonb,
  variant integer not null default 0,
  audience_member_id uuid references public.league_members (member_id) on delete cascade
);
create index events_league_idx on public.events (league_id, ts);

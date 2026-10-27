-- Row level security and grants (docs/ARCHITECTURE.md §5).
-- Clients never write: no INSERT/UPDATE/DELETE policy exists; every write goes through a
-- security definer RPC. Reads are granted table by table below.

-- Helpers used by policies. security definer so they can read league_members without
-- recursing into its own policy; they only return booleans or the caller's own member id.
create function private.my_member_id(p_league uuid)
returns uuid
language sql
stable
security definer
set search_path = ''
as $$
  select m.member_id from public.league_members m
  where m.league_id = p_league and m.user_id = auth.uid()
$$;

create function private.is_league_member(p_league uuid)
returns boolean
language sql
stable
security definer
set search_path = ''
as $$ select private.my_member_id(p_league) is not null $$;

create function private.is_shadow(p_member uuid)
returns boolean
language sql
stable
security definer
set search_path = ''
as $$
  select coalesce((select m.commander = 'shadow' from public.league_members m
                   where m.member_id = p_member), false)
$$;

-- Squads: owner always; other members from lock_at; a Shadow's squad only from debrief_at.
create function private.can_see_squad(p_league uuid, p_week date, p_member uuid)
returns boolean
language plpgsql
stable
security definer
set search_path = ''
as $$
declare
  v_me uuid := private.my_member_id(p_league);
  v_week public.weeks;
begin
  if v_me is null then
    return false;
  end if;
  if v_me = p_member then
    return true;
  end if;
  select * into v_week from public.weeks w where w.league_id = p_league and w.week = p_week;
  if not found then
    return false;
  end if;
  if private.is_shadow(p_member) then
    return v_week.debrief_at is not null and private.clock() >= v_week.debrief_at;
  end if;
  return private.clock() >= v_week.lock_at;
end;
$$;

-- Swaps: owner always; others once applied (resupply_closes_at); a Shadow's from debrief_at.
create function private.can_see_swaps(p_league uuid, p_week date, p_member uuid)
returns boolean
language plpgsql
stable
security definer
set search_path = ''
as $$
declare
  v_me uuid := private.my_member_id(p_league);
  v_week public.weeks;
begin
  if v_me is null then
    return false;
  end if;
  if v_me = p_member then
    return true;
  end if;
  select * into v_week from public.weeks w where w.league_id = p_league and w.week = p_week;
  if not found then
    return false;
  end if;
  if private.is_shadow(p_member) then
    return v_week.debrief_at is not null and private.clock() >= v_week.debrief_at;
  end if;
  return private.clock() >= v_week.resupply_closes_at;
end;
$$;

-- A member is jammed once a jamming order against them has been applied this week.
create function private.is_jammed(p_league uuid, p_week date, p_member uuid)
returns boolean
language sql
stable
security definer
set search_path = ''
as $$
  select exists (
    select 1 from public.orders o
    where o.league_id = p_league and o.week = p_week and o.target_member_id = p_member
      and o.type = 'jamming' and o.status = 'applied'
  )
$$;

revoke execute on all functions in schema private from public, anon, authenticated;
grant execute on function
  private.my_member_id(uuid),
  private.is_league_member(uuid),
  private.can_see_squad(uuid, date, uuid),
  private.can_see_swaps(uuid, date, uuid),
  private.is_jammed(uuid, date, uuid),
  private.clock()
to authenticated;

-- Enable RLS everywhere.
alter table public.game_config enable row level security;
alter table public.profiles enable row level security;
alter table public.leagues enable row level security;
alter table public.league_members enable row level security;
alter table public.instruments enable row level security;
alter table public.instrument_weeks enable row level security;
alter table public.reference_prices enable row level security;
alter table public.prices_live enable row level security;
alter table public.weeks enable row level security;
alter table public.market_runs enable row level security;
alter table public.job_runs enable row level security;
alter table public.squads enable row level security;
alter table public.squad_units enable row level security;
alter table public.swaps enable row level security;
alter table public.ammo_ledger enable row level security;
alter table public.orders enable row level security;
alter table public.pacts enable row level security;
alter table public.scores_live enable row level security;
alter table public.scores_live_public enable row level security;
alter table public.scores_final enable row level security;
alter table public.badges enable row level security;
alter table public.events enable row level security;

-- Grants: API roles read only what is listed here; anon reads nothing.
revoke all on all tables in schema public from anon, authenticated;
revoke all on all sequences in schema public from anon, authenticated;
grant select on
  public.game_config, public.profiles, public.leagues, public.league_members,
  public.instruments, public.instrument_weeks, public.reference_prices, public.prices_live,
  public.weeks, public.squads, public.squad_units, public.swaps, public.ammo_ledger,
  public.orders, public.pacts, public.scores_live, public.scores_live_public,
  public.scores_final, public.badges, public.events
to authenticated;
-- Jobs (service role, bypasses RLS) write everything.
grant all on all tables in schema public to service_role;
grant all on all sequences in schema public to service_role;

-- Public reference data.
create policy "authenticated read" on public.game_config for select to authenticated using (true);
create policy "authenticated read" on public.instruments for select to authenticated using (true);
create policy "authenticated read" on public.instrument_weeks for select to authenticated using (true);
create policy "authenticated read" on public.reference_prices for select to authenticated using (true);
create policy "authenticated read" on public.prices_live for select to authenticated using (true);

create policy "own profile" on public.profiles
  for select to authenticated using (id = auth.uid());

-- League-wide data: members of that league.
create policy "members read" on public.leagues
  for select to authenticated using (private.is_league_member(id));
create policy "members read" on public.league_members
  for select to authenticated using (private.is_league_member(league_id));
create policy "members read" on public.weeks
  for select to authenticated using (private.is_league_member(league_id));
create policy "members read" on public.scores_live_public
  for select to authenticated using (private.is_league_member(league_id));
create policy "members read" on public.scores_final
  for select to authenticated using (private.is_league_member(league_id));
create policy "members read" on public.badges
  for select to authenticated using (private.is_league_member(league_id));

create policy "visible squads" on public.squads
  for select to authenticated using (private.can_see_squad(league_id, week, member_id));
create policy "visible squads" on public.squad_units
  for select to authenticated using (private.can_see_squad(league_id, week, member_id));
create policy "visible swaps" on public.swaps
  for select to authenticated using (private.can_see_swaps(league_id, week, member_id));

-- Owner only.
create policy "own ammo" on public.ammo_ledger
  for select to authenticated using (member_id = private.my_member_id(league_id));
create policy "own orders" on public.orders
  for select to authenticated using (member_id = private.my_member_id(league_id));
create policy "own live score unless jammed" on public.scores_live
  for select to authenticated using (
    member_id = private.my_member_id(league_id)
    and not private.is_jammed(league_id, week, member_id)
  );

-- Pacts: active ones are public to the league; proposals only to the two players.
create policy "visible pacts" on public.pacts
  for select to authenticated using (
    private.is_league_member(league_id)
    and (
      status = 'active'
      or private.my_member_id(league_id) in (proposer_member_id, partner_member_id)
    )
  );

-- Events: members, filtered by audience.
create policy "audience" on public.events
  for select to authenticated using (
    private.is_league_member(league_id)
    and (audience_member_id is null or audience_member_id = private.my_member_id(league_id))
  );

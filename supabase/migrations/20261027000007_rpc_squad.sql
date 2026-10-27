-- Squad RPCs (GAME_RULES §3): draft during briefing, swaps during resupply.

create function private.require_active_member(p_league uuid)
returns public.league_members
language plpgsql
security definer
set search_path = ''
as $$
declare
  v_member public.league_members := private.require_member(p_league);
begin
  if (select l.status from public.leagues l where l.id = p_league) <> 'active' then
    perform private.raise_error('LEAGUE_NOT_ACTIVE');
  end if;
  return v_member;
end;
$$;

-- The week whose briefing is open now (deadline checked on the clock, not on `phase`).
create function private.briefing_week(p_league uuid)
returns public.weeks
language plpgsql
security definer
set search_path = ''
as $$
declare
  v_week public.weeks;
begin
  select * into v_week from public.weeks w
  where w.league_id = p_league and private.clock() < w.lock_at
  order by w.week
  limit 1;
  if not found then
    perform private.raise_error('BRIEFING_CLOSED');
  end if;
  return v_week;
end;
$$;

-- The week whose resupply window is open now.
create function private.resupply_week(p_league uuid)
returns public.weeks
language plpgsql
security definer
set search_path = ''
as $$
declare
  v_week public.weeks;
begin
  select * into v_week from public.weeks w
  where w.league_id = p_league
    and w.resupply_opens_at is not null
    and private.clock() >= w.resupply_opens_at
    and private.clock() < w.resupply_closes_at
  order by w.week
  limit 1;
  if not found then
    perform private.raise_error('RESUPPLY_CLOSED');
  end if;
  return v_week;
end;
$$;

create function private.is_blockaded(p_league uuid, p_week date, p_member uuid)
returns boolean
language sql
stable
security definer
set search_path = ''
as $$
  select exists (
    select 1 from public.orders o
    where o.league_id = p_league and o.week = p_week and o.target_member_id = p_member
      and o.type = 'blockade' and o.status = 'applied'
  )
$$;

-- Validates a front given as {slot: instrument_id} for the 5 front slots.
create function private.check_front(p_week date, p_front jsonb)
returns void
language plpgsql
stable
security definer
set search_path = ''
as $$
declare
  v_min integer := private.cfg_int('front_min_per_region');
  v_region public.region;
  v_count integer;
  v_target integer := (p_front ->> 'priority_target')::integer;
begin
  foreach v_region in array enum_range(null::public.region) loop
    select count(*) into v_count
    from jsonb_each_text(p_front) f
    join public.instruments i on i.id = f.value::integer
    where i.region = v_region;
    if v_count < v_min then
      perform private.raise_error('FRONT_NEEDS_REGION',
        jsonb_build_object('region', v_region, 'min', v_min, 'count', v_count));
    end if;
  end loop;

  if (select i.region from public.instruments i where i.id = (p_front ->> 'champion')::integer)
     = (select i.region from public.instruments i where i.id = (p_front ->> 'veteran')::integer) then
    perform private.raise_error('VETERAN_SAME_REGION');
  end if;

  if not exists (select 1 from public.instrument_weeks iw
                 where iw.week = p_week and iw.in_conflict_zone) then
    perform private.raise_error('CONFLICT_ZONE_NOT_READY');
  end if;
  if not exists (select 1 from public.instrument_weeks iw
                 where iw.week = p_week and iw.instrument_id = v_target and iw.in_conflict_zone) then
    perform private.raise_error('PRIORITY_TARGET_NOT_IN_ZONE');
  end if;
end;
$$;

-- Current front of a squad as {slot: instrument_id}, after pending swaps (optionally
-- ignoring the swap of one slot).
create function private.front_after_swaps(
  p_league uuid, p_week date, p_member uuid, p_ignore_slot public.slot
)
returns jsonb
language sql
stable
security definer
set search_path = ''
as $$
  select coalesce(jsonb_object_agg(u.slot, coalesce(r.instrument_id, u.instrument_id)), '{}'::jsonb)
  from public.squad_units u
  left join public.swaps s
    on s.league_id = u.league_id and s.week = u.week and s.member_id = u.member_id
   and s.slot = u.slot and s.slot is distinct from p_ignore_slot
  left join public.squad_units r
    on r.league_id = s.league_id and r.week = s.week and r.member_id = s.member_id
   and r.slot = s.reserve_slot
  where u.league_id = p_league and u.week = p_week and u.member_id = p_member
    and u.slot::text = any (select jsonb_array_elements_text(private.cfg('front_slots')))
$$;

-- p_units: {"champion": <instrument id>, ..., "reserve_1": <id>, ...}
create function public.save_squad(p_league uuid, p_units jsonb)
returns void
language plpgsql
security definer
set search_path = ''
as $$
declare
  v_member public.league_members := private.require_active_member(p_league);
  v_week public.weeks := private.briefing_week(p_league);
  v_front_slots text[] := array(select jsonb_array_elements_text(private.cfg('front_slots')));
  v_reserve_size integer := case when v_member.commander = 'quartermaster'
                                 then private.cfg_int('quartermaster_reserve_size')
                                 else private.cfg_int('reserve_size') end;
  v_reserve_slots text[];
  v_reserve_min integer := private.cfg_int('reserve_min_per_region');
  v_key text;
  v_value jsonb;
  v_front jsonb := '{}'::jsonb;
  v_region public.region;
  v_count integer;
begin
  v_reserve_slots := (array(select jsonb_array_elements_text(private.cfg('reserve_slots'))))[1:v_reserve_size];
  if p_units is null or jsonb_typeof(p_units) <> 'object' then
    perform private.raise_error('SQUAD_INVALID');
  end if;

  for v_key, v_value in select e.key, e.value from jsonb_each(p_units) e loop
    if not (v_key = any (v_front_slots) or v_key = any (v_reserve_slots)) then
      perform private.raise_error('SQUAD_UNKNOWN_SLOT', jsonb_build_object('slot', v_key));
    end if;
    if jsonb_typeof(v_value) <> 'number'
       or not exists (select 1 from public.instruments i where i.id = (v_value #>> '{}')::integer) then
      perform private.raise_error('UNKNOWN_INSTRUMENT', jsonb_build_object('slot', v_key));
    end if;
  end loop;

  foreach v_key in array v_front_slots || v_reserve_slots loop
    if not (p_units ? v_key) then
      perform private.raise_error('SQUAD_MISSING_SLOT', jsonb_build_object('slot', v_key));
    end if;
  end loop;

  if (select count(distinct e.value) from jsonb_each(p_units) e)
     <> (select count(*) from jsonb_each(p_units)) then
    perform private.raise_error('SQUAD_DUPLICATE_INSTRUMENT');
  end if;

  foreach v_key in array v_front_slots loop
    v_front := v_front || jsonb_build_object(v_key, p_units -> v_key);
  end loop;
  perform private.check_front(v_week.week, v_front);

  foreach v_region in array enum_range(null::public.region) loop
    select count(*) into v_count
    from unnest(v_reserve_slots) s(slot)
    join public.instruments i on i.id = (p_units ->> s.slot)::integer
    where i.region = v_region;
    if v_count < v_reserve_min then
      perform private.raise_error('RESERVE_NEEDS_REGION',
        jsonb_build_object('region', v_region, 'min', v_reserve_min));
    end if;
  end loop;

  insert into public.squads (league_id, week, member_id, locked, auto, submitted_at)
  values (p_league, v_week.week, v_member.member_id, false, false, private.clock())
  on conflict (league_id, week, member_id)
  do update set submitted_at = excluded.submitted_at, auto = false;

  delete from public.squad_units u
  where u.league_id = p_league and u.week = v_week.week and u.member_id = v_member.member_id;

  insert into public.squad_units (league_id, week, member_id, slot, instrument_id,
                                  active_s1, active_s2)
  select p_league, v_week.week, v_member.member_id, e.key::public.slot, (e.value #>> '{}')::integer,
         e.key = any (v_front_slots), e.key = any (v_front_slots)
  from jsonb_each(p_units) e;
end;
$$;

-- Schedules (or replaces) the swap of one front slot with a reserve unit.
create function public.swap_unit(p_league uuid, p_slot public.slot, p_reserve_slot public.slot)
returns void
language plpgsql
security definer
set search_path = ''
as $$
declare
  v_member public.league_members := private.require_active_member(p_league);
  v_week public.weeks := private.resupply_week(p_league);
  v_max integer := case when v_member.commander = 'quartermaster'
                        then private.cfg_int('quartermaster_max_swaps')
                        else private.cfg_int('max_swaps') end;
  v_reserve_instrument integer;
  v_front jsonb;
begin
  if not exists (select 1 from public.squads s
                 where s.league_id = p_league and s.week = v_week.week
                   and s.member_id = v_member.member_id) then
    perform private.raise_error('NO_SQUAD');
  end if;
  if private.is_blockaded(p_league, v_week.week, v_member.member_id) then
    perform private.raise_error('BLOCKADED');
  end if;
  if p_slot is null
     or not (p_slot::text = any (select jsonb_array_elements_text(private.cfg('front_slots')))) then
    perform private.raise_error('SWAP_INVALID_SLOT');
  end if;
  select u.instrument_id into v_reserve_instrument from public.squad_units u
  where u.league_id = p_league and u.week = v_week.week and u.member_id = v_member.member_id
    and u.slot = p_reserve_slot
    and u.slot::text = any (select jsonb_array_elements_text(private.cfg('reserve_slots')));
  if v_reserve_instrument is null then
    perform private.raise_error('RESERVE_SLOT_EMPTY');
  end if;
  if exists (select 1 from public.swaps s
             where s.league_id = p_league and s.week = v_week.week
               and s.member_id = v_member.member_id
               and s.reserve_slot = p_reserve_slot and s.slot <> p_slot) then
    perform private.raise_error('RESERVE_ALREADY_USED');
  end if;
  if (select count(*) from public.swaps s
      where s.league_id = p_league and s.week = v_week.week
        and s.member_id = v_member.member_id and s.slot <> p_slot) + 1 > v_max then
    perform private.raise_error('SWAP_LIMIT', jsonb_build_object('max', v_max));
  end if;

  v_front := private.front_after_swaps(p_league, v_week.week, v_member.member_id, p_slot)
             || jsonb_build_object(p_slot::text, v_reserve_instrument);
  perform private.check_front(v_week.week, v_front);

  delete from public.swaps s
  where s.league_id = p_league and s.week = v_week.week
    and s.member_id = v_member.member_id and s.slot = p_slot;
  insert into public.swaps (league_id, week, member_id, slot, reserve_slot, created_at)
  values (p_league, v_week.week, v_member.member_id, p_slot, p_reserve_slot, private.clock());
end;
$$;

create function public.cancel_swap(p_league uuid, p_slot public.slot)
returns void
language plpgsql
security definer
set search_path = ''
as $$
declare
  v_member public.league_members := private.require_active_member(p_league);
  v_week public.weeks := private.resupply_week(p_league);
begin
  if not exists (select 1 from public.swaps s
                 where s.league_id = p_league and s.week = v_week.week
                   and s.member_id = v_member.member_id and s.slot = p_slot) then
    perform private.raise_error('NO_SUCH_SWAP');
  end if;
  -- The remaining swaps must still give a valid front.
  perform private.check_front(
    v_week.week, private.front_after_swaps(p_league, v_week.week, v_member.member_id, p_slot));
  delete from public.swaps s
  where s.league_id = p_league and s.week = v_week.week
    and s.member_id = v_member.member_id and s.slot = p_slot;
end;
$$;

revoke execute on function
  public.save_squad(uuid, jsonb),
  public.swap_unit(uuid, public.slot, public.slot),
  public.cancel_swap(uuid, public.slot)
from public, anon;
grant execute on function
  public.save_squad(uuid, jsonb),
  public.swap_unit(uuid, public.slot, public.slot),
  public.cancel_swap(uuid, public.slot)
to authenticated;

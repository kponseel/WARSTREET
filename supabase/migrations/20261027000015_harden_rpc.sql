-- Milestone 09 hardening, found by supabase/tests/test_rpc_fuzz.py.
--
-- save_squad: a unit id that is a JSON number but not a small whole number (1.5, 1.0,
-- 1e12) reached an integer cast and failed with an internal error instead of the
-- UNKNOWN_INSTRUMENT code. Same function otherwise; its grants are kept.

create or replace function public.save_squad(p_league uuid, p_units jsonb)
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
    -- A whole number that fits an integer: 1.5, 1.0 or 1e12 are refused, never cast.
    if jsonb_typeof(v_value) <> 'number' or (v_value #>> '{}') !~ '^[0-9]{1,9}$' then
      perform private.raise_error('UNKNOWN_INSTRUMENT', jsonb_build_object('slot', v_key));
    end if;
    if not exists (select 1 from public.instruments i where i.id = (v_value #>> '{}')::integer) then
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

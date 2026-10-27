-- Orders (GAME_RULES §6) and pacts (§7). Orders are validated and paid here; they resolve
-- when their window closes (jobs), except `intel`, which resolves immediately.

-- The strict campaign leader before the given week (no tie), or null.
create function private.bounty_member(p_league uuid, p_week date)
returns uuid
language sql
stable
security definer
set search_path = ''
as $$
  with standings as (
    select m.member_id, coalesce(sum(f.campaign_points), 0) as points
    from public.league_members m
    left join public.scores_final f on f.member_id = m.member_id and f.week < p_week
    where m.league_id = p_league and not m.is_drone
    group by m.member_id
  ), top as (
    select s.member_id from standings s
    where s.points = (select max(points) from standings)
  )
  select t.member_id from top t where (select count(*) from top) = 1
$$;

create function private.ammo_balance(p_member uuid)
returns integer
language sql
stable
security definer
set search_path = ''
as $$
  select coalesce(sum(l.delta), 0)::integer from public.ammo_ledger l where l.member_id = p_member
$$;

create function private.in_cfg_list(p_key text, p_value text)
returns boolean
language sql
stable
set search_path = ''
as $$ select private.cfg(p_key) ? p_value $$;

create function public.play_order(
  p_league uuid,
  p_type public.order_type,
  p_target_member uuid default null,
  p_target_slot public.slot default null
)
returns uuid
language plpgsql
security definer
set search_path = ''
as $$
declare
  v_member public.league_members := private.require_active_member(p_league);
  v_league public.leagues := private.lock_league(p_league);  -- serialises ammo and caps
  v_now timestamptz := private.clock();
  v_week public.weeks;
  v_window public.order_window;
  v_spec jsonb;
  v_target public.league_members;
  v_cost integer;
  v_balance integer;
  v_order uuid := gen_random_uuid();
  v_units jsonb;
begin
  if p_type is null then
    perform private.raise_error('ORDER_INVALID');
  end if;

  select * into v_week from public.weeks w
  where w.league_id = p_league and v_now < w.lock_at order by w.week limit 1;
  if found then
    v_window := 'briefing';
  else
    select * into v_week from public.weeks w
    where w.league_id = p_league and w.resupply_opens_at is not null
      and v_now >= w.resupply_opens_at and v_now < w.resupply_closes_at
    order by w.week limit 1;
    if not found then
      perform private.raise_error('ORDER_WINDOW_CLOSED');
    end if;
    v_window := 'resupply';
  end if;

  v_spec := private.cfg('orders') -> p_type::text;
  if not (v_spec -> 'windows' ? v_window::text) then
    perform private.raise_error('ORDER_WRONG_WINDOW', jsonb_build_object('window', v_window));
  end if;
  if v_member.commander = 'berserker'
     and private.in_cfg_list('berserker_forbidden_orders', p_type::text) then
    perform private.raise_error('COMMANDER_FORBIDS_ORDER');
  end if;
  if v_window = 'resupply' and private.is_blockaded(p_league, v_week.week, v_member.member_id) then
    perform private.raise_error('BLOCKADED');
  end if;
  if private.in_cfg_list('once_per_week_orders', p_type::text)
     and exists (select 1 from public.orders o
                 where o.member_id = v_member.member_id and o.week = v_week.week
                   and o.type = p_type and o.status <> 'rejected') then
    perform private.raise_error('ORDER_ONCE_PER_WEEK');
  end if;

  -- Target player.
  if private.in_cfg_list('targeted_orders', p_type::text) then
    if p_target_member is null then
      perform private.raise_error('TARGET_REQUIRED');
    end if;
    select * into v_target from public.league_members m
    where m.member_id = p_target_member and m.league_id = p_league and not m.is_drone;
    if not found or v_target.member_id = v_member.member_id then
      perform private.raise_error('INVALID_TARGET');
    end if;
    if p_type = 'intel' and v_target.commander = 'shadow' then
      perform private.raise_error('TARGET_IMMUNE_TO_INTEL');
    end if;
  elsif p_target_member is not null then
    perform private.raise_error('TARGET_NOT_ALLOWED');
  end if;

  -- Target slot.
  if private.in_cfg_list('orders_with_target_slot', p_type::text) then
    if p_target_slot is null then
      perform private.raise_error('TARGET_SLOT_REQUIRED');
    end if;
    if not private.in_cfg_list('front_slots', p_target_slot::text)
       or (p_type = 'field_promotion' and p_target_slot = 'champion') then
      perform private.raise_error('TARGET_SLOT_INVALID');
    end if;
  elsif p_target_slot is not null then
    perform private.raise_error('TARGET_SLOT_NOT_ALLOWED');
  end if;

  -- Attacks: cap per target and Bounty discount.
  v_cost := (v_spec ->> 'cost')::integer;
  if v_spec ->> 'kind' = 'attack' then
    if (select count(*) from public.orders o
        where o.league_id = p_league and o.week = v_week.week
          and o.target_member_id = v_target.member_id and o.status <> 'rejected'
          and (private.cfg('orders') -> o.type::text ->> 'kind') = 'attack')
       >= private.cfg_int('attack_cap_per_week') then
      perform private.raise_error('ATTACK_CAP_REACHED',
        jsonb_build_object('max', private.cfg_int('attack_cap_per_week')));
    end if;
    if private.bounty_member(p_league, v_week.week) = v_target.member_id then
      v_cost := greatest(private.cfg_int('min_order_cost'),
                         v_cost - private.cfg_int('bounty_discount'));
    end if;
  end if;

  v_balance := private.ammo_balance(v_member.member_id);
  if v_balance < v_cost then
    perform private.raise_error('NOT_ENOUGH_AMMO',
      jsonb_build_object('cost', v_cost, 'balance', v_balance));
  end if;

  insert into public.orders (id, league_id, week, member_id, type, target_member_id, target_slot,
                             order_window, cost, status, created_at, resolved_at)
  values (v_order, p_league, v_week.week, v_member.member_id, p_type, p_target_member,
          p_target_slot, v_window, v_cost,
          case when p_type = 'intel' then 'applied' else 'pending' end::public.order_status,
          v_now, case when p_type = 'intel' then v_now end);
  insert into public.ammo_ledger (league_id, member_id, week, delta, reason, order_id, created_at)
  values (p_league, v_member.member_id, v_week.week, -v_cost, 'order', v_order, v_now);

  -- intel: one-time snapshot of the target's current draft, for the attacker only.
  if p_type = 'intel' then
    select coalesce(jsonb_object_agg(u.slot, i.ticker), '{}'::jsonb) into v_units
    from public.squad_units u join public.instruments i on i.id = u.instrument_id
    where u.league_id = p_league and u.week = v_week.week and u.member_id = v_target.member_id;
    insert into public.events (league_id, week, ts, kind, template_key, vars, audience_member_id)
    values (p_league, v_week.week, v_now, 'intel', 'event.intel.snapshot',
            jsonb_build_object('target_member_id', v_target.member_id, 'units', v_units,
                               'taken_at', v_now),
            v_member.member_id);
  end if;
  return v_order;
end;
$$;

create function private.has_active_pact(p_league uuid, p_week date, p_member uuid)
returns boolean
language sql
stable
security definer
set search_path = ''
as $$
  select exists (
    select 1 from public.pacts p
    where p.league_id = p_league and p.week = p_week and p.status = 'active'
      and p_member in (p.proposer_member_id, p.partner_member_id)
  )
$$;

create function public.propose_pact(p_league uuid, p_partner uuid)
returns uuid
language plpgsql
security definer
set search_path = ''
as $$
declare
  v_member public.league_members := private.require_active_member(p_league);
  v_league public.leagues := private.lock_league(p_league);
  v_week public.weeks := private.briefing_week(p_league);
  v_pact uuid := gen_random_uuid();
begin
  if p_partner is null or p_partner = v_member.member_id or not exists (
       select 1 from public.league_members m
       where m.member_id = p_partner and m.league_id = p_league and not m.is_drone) then
    perform private.raise_error('INVALID_TARGET');
  end if;
  if private.has_active_pact(p_league, v_week.week, v_member.member_id)
     or private.has_active_pact(p_league, v_week.week, p_partner) then
    perform private.raise_error('PACT_ALREADY_ACTIVE');
  end if;
  if exists (select 1 from public.pacts p
             where p.league_id = p_league and p.week = v_week.week and p.status = 'proposed'
               and array[p.proposer_member_id, p.partner_member_id]
                   @> array[v_member.member_id, p_partner]) then
    perform private.raise_error('PACT_ALREADY_PROPOSED');
  end if;
  insert into public.pacts (id, league_id, week, proposer_member_id, partner_member_id,
                            created_at)
  values (v_pact, p_league, v_week.week, v_member.member_id, p_partner, private.clock());
  return v_pact;
end;
$$;

create function private.lock_pact_for_partner(p_pact uuid)
returns public.pacts
language plpgsql
security definer
set search_path = ''
as $$
declare
  v_pact public.pacts;
  v_member public.league_members;
  v_week public.weeks;
begin
  select * into v_pact from public.pacts p where p.id = p_pact for update;
  if not found then
    perform private.raise_error('PACT_NOT_FOUND');
  end if;
  v_member := private.require_active_member(v_pact.league_id);
  if v_pact.partner_member_id <> v_member.member_id then
    perform private.raise_error('NOT_PACT_PARTNER');
  end if;
  if v_pact.status <> 'proposed' then
    perform private.raise_error('PACT_NOT_PENDING');
  end if;
  v_week := private.briefing_week(v_pact.league_id);
  if v_week.week <> v_pact.week then
    perform private.raise_error('BRIEFING_CLOSED');
  end if;
  return v_pact;
end;
$$;

create function public.accept_pact(p_pact uuid)
returns void
language plpgsql
security definer
set search_path = ''
as $$
declare
  v_pact public.pacts := private.lock_pact_for_partner(p_pact);
  v_league public.leagues := private.lock_league(v_pact.league_id);
  v_now timestamptz := private.clock();
begin
  if private.has_active_pact(v_pact.league_id, v_pact.week, v_pact.proposer_member_id)
     or private.has_active_pact(v_pact.league_id, v_pact.week, v_pact.partner_member_id) then
    perform private.raise_error('PACT_ALREADY_ACTIVE');
  end if;
  update public.pacts p set status = 'active', responded_at = v_now where p.id = v_pact.id;
  -- The other proposals of both players are cancelled (max 1 active pact per week).
  update public.pacts p set status = 'cancelled', responded_at = v_now
  where p.league_id = v_pact.league_id and p.week = v_pact.week and p.status = 'proposed'
    and (p.proposer_member_id in (v_pact.proposer_member_id, v_pact.partner_member_id)
         or p.partner_member_id in (v_pact.proposer_member_id, v_pact.partner_member_id));
end;
$$;

create function public.decline_pact(p_pact uuid)
returns void
language plpgsql
security definer
set search_path = ''
as $$
declare
  v_pact public.pacts := private.lock_pact_for_partner(p_pact);
begin
  update public.pacts p set status = 'declined', responded_at = private.clock()
  where p.id = v_pact.id;
end;
$$;

revoke execute on function
  public.play_order(uuid, public.order_type, uuid, public.slot),
  public.propose_pact(uuid, uuid),
  public.accept_pact(uuid),
  public.decline_pact(uuid)
from public, anon;
grant execute on function
  public.play_order(uuid, public.order_type, uuid, public.slot),
  public.propose_pact(uuid, uuid),
  public.accept_pact(uuid),
  public.decline_pact(uuid)
to authenticated;

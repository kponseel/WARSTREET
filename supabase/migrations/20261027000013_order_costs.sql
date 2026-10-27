-- What each order would cost the caller right now (milestone 06): the current window's
-- orders, per target for targeted ones, with the Bounty discount. The app shows these
-- exact prices instead of recomputing the rule; play_order stays the authority.
-- Empty when no order window is open. A Berserker does not see its forbidden orders.
create function public.order_costs(p_league uuid)
returns table (
  order_window public.order_window,
  type public.order_type,
  target_member_id uuid,
  cost integer,
  target_has_bounty boolean
)
language plpgsql
stable
security definer
set search_path = ''
as $$
declare
  v_member public.league_members := private.require_active_member(p_league);
  v_now timestamptz := private.clock();
  v_week public.weeks;
  v_window public.order_window;
  v_bounty uuid;
begin
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
      return;
    end if;
    v_window := 'resupply';
  end if;
  v_bounty := private.bounty_member(p_league, v_week.week);
  return query
  select
    v_window,
    o.key::public.order_type,
    t.member_id,
    case
      when o.value ->> 'kind' = 'attack' and t.member_id = v_bounty
        then greatest(private.cfg_int('min_order_cost'),
                      (o.value ->> 'cost')::integer - private.cfg_int('bounty_discount'))
      else (o.value ->> 'cost')::integer
    end,
    coalesce(t.member_id = v_bounty, false)
  from jsonb_each(private.cfg('orders')) o
  left join lateral (
    select m.member_id from public.league_members m
    where private.in_cfg_list('targeted_orders', o.key)
      and m.league_id = p_league and not m.is_drone and m.member_id <> v_member.member_id
  ) t on true
  where o.value -> 'windows' ? v_window::text
    and not (v_member.commander = 'berserker'
             and private.in_cfg_list('berserker_forbidden_orders', o.key))
  order by o.key, t.member_id;
end;
$$;

revoke execute on function public.order_costs(uuid) from public, anon;
grant execute on function public.order_costs(uuid) to authenticated;

-- Read views (docs/ARCHITECTURE.md §5). security_invoker = true by default so the caller's
-- RLS applies; orders_public must mask data, so it runs with owner rights and filters on
-- league membership itself.

-- Other players' orders, after resolution. The attacker is masked when it is a Shadow
-- (anonymous orders); a force field shows only once it was triggered (status applied).
create view public.orders_public
with (security_barrier = true)
as
select
  o.id,
  o.league_id,
  o.week,
  o.type,
  case when private.is_shadow(o.member_id) then null else o.member_id end as member_id,
  o.target_member_id,
  o.target_slot,
  o.order_window,
  o.status,
  o.resolved_at
from public.orders o
where private.is_league_member(o.league_id)
  and o.resolved_at is not null
  and o.status in ('applied', 'blocked')
  and (o.type <> 'force_field' or o.status = 'applied');

create view public.squads_visible
with (security_invoker = true)
as
select
  u.league_id,
  u.week,
  u.member_id,
  u.slot,
  u.instrument_id,
  i.ticker,
  i.name,
  i.region,
  i.sector,
  u.active_s1,
  u.active_s2
from public.squad_units u
join public.instruments i on i.id = u.instrument_id;

create view public.ammo_balance
with (security_invoker = true)
as
select l.league_id, l.member_id, sum(l.delta)::integer as balance
from public.ammo_ledger l
group by l.league_id, l.member_id;

-- Campaign standings of humans: points, weekly wins (tiebreak 1), cumulative PF (tiebreak 2).
create view public.campaign_standings
with (security_invoker = true)
as
select
  m.league_id,
  m.member_id,
  coalesce(sum(f.campaign_points), 0) as campaign_points,
  count(*) filter (where f.rank = 1)::integer as weekly_wins,
  coalesce(sum(f.pf_total), 0)::integer as pf_cumulative
from public.league_members m
left join public.scores_final f on f.member_id = m.member_id
where not m.is_drone
group by m.league_id, m.member_id;

-- Function EXECUTE inside a view is checked against the caller, not the view owner.
-- is_shadow only answers "is this member a Shadow?", which the lobby already shows.
grant execute on function private.is_shadow(uuid) to authenticated;

revoke all on public.orders_public, public.squads_visible, public.ammo_balance,
  public.campaign_standings from anon, authenticated;
grant select on public.orders_public, public.squads_visible, public.ammo_balance,
  public.campaign_standings to authenticated;
grant select on public.orders_public, public.squads_visible, public.ammo_balance,
  public.campaign_standings to service_role;

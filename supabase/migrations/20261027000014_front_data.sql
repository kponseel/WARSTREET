-- Data for the live front (milestone 07). Both are display-only; scores stay in the jobs.

-- Trading sessions of the week per exchange, written by the market job from
-- exchange_calendars (holidays, half days, DST), so the app never hardcodes market hours
-- (daily phase banner: European Assault / Crossfire / US Counter-offensive).
create table public.market_sessions (
  mic text not null,
  session date not null,
  open_at timestamptz not null,
  close_at timestamptz not null,
  primary key (mic, session)
);
alter table public.market_sessions enable row level security;
revoke all on public.market_sessions from anon, authenticated;
grant select on public.market_sessions to authenticated;
grant all on public.market_sessions to service_role;
create policy "authenticated read" on public.market_sessions
  for select to authenticated using (true);

-- Each instrument's move this week: last live quote (or the final P_end) against P0.
-- Prices and returns are visible to everyone (GAME_RULES §6: jamming hides points, not
-- prices); the app shows them next to units without computing anything.
create view public.live_returns
with (security_invoker = true)
as
select
  p0.instrument_id,
  p0.week,
  p0.price as p0,
  coalesce(fin.price, last.price) as last_price,
  coalesce(fin.fetched_at, last.ts) as last_at,
  round((coalesce(fin.price, last.price) / p0.price - 1) * 100, 2) as week_return_pct
from public.reference_prices p0
left join public.reference_prices fin
  on fin.instrument_id = p0.instrument_id and fin.week = p0.week and fin.kind = 'p_end'
left join lateral (
  select l.price, l.ts from public.prices_live l
  where l.instrument_id = p0.instrument_id
    and l.ts >= p0.week and l.ts < p0.week + 7
  order by l.ts desc
  limit 1
) last on true
where p0.kind = 'p0' and p0.price > 0;

revoke all on public.live_returns from anon, authenticated;
grant select on public.live_returns to authenticated;
grant select on public.live_returns to service_role;

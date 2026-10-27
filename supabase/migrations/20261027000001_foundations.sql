-- Foundations: enums, private schema, helpers (config, clock, errors), default privileges.
-- Security model: docs/ARCHITECTURE.md §5.

-- Nothing new is executable or readable by API roles unless granted explicitly.
-- PUBLIC's EXECUTE on functions is a global default: it can only be revoked globally
-- (per-schema default privileges can add rights, never remove them).
alter default privileges revoke execute on functions from public;
-- Supabase grants API roles rights in `public` per schema; revoke those per schema.
alter default privileges in schema public revoke execute on functions from anon, authenticated;
alter default privileges in schema public revoke all on tables from anon, authenticated;
alter default privileges in schema public revoke all on sequences from anon, authenticated;

create type public.league_status as enum ('lobby', 'active', 'finished');
create type public.phase as enum ('briefing', 's1_live', 'resupply', 's2_live', 'debrief');
create type public.slot as enum (
  'champion', 'veteran', 'marksman', 'saboteur', 'priority_target',
  'reserve_1', 'reserve_2', 'reserve_3'
);
create type public.commander as enum (
  'bastion', 'berserker', 'prophet', 'hunter', 'shadow', 'technomancer', 'quartermaster'
);
create type public.region as enum ('EU', 'US');
create type public.locale as enum ('en', 'fr');
create type public.order_type as enum (
  'orbital_strike', 'pillage', 'blockade', 'jamming', 'force_field',
  'tactical_retreat', 'field_promotion', 'reversal', 'intel'
);
create type public.order_window as enum ('briefing', 'resupply');
create type public.order_status as enum ('pending', 'applied', 'blocked', 'rejected');
create type public.pact_status as enum ('proposed', 'active', 'declined', 'cancelled');
create type public.price_kind as enum ('p0', 'p_mid', 'p_end');

-- Internal helpers live here; this schema is not exposed by the API.
create schema private;
revoke all on schema private from public;
grant usage on schema private to authenticated, service_role;

-- Rule values (generated from engine/config.py by supabase/scripts/generate_seed.py).
create table public.game_config (
  key text primary key,
  value jsonb not null
);

create function private.cfg(p_key text)
returns jsonb
language plpgsql
stable
security definer
set search_path = ''
as $$
declare
  v jsonb;
begin
  select c.value into v from public.game_config c where c.key = p_key;
  if v is null then
    raise exception 'missing game_config key %', p_key;
  end if;
  return v;
end;
$$;

create function private.cfg_int(p_key text)
returns integer
language sql
stable
set search_path = ''
as $$ select (private.cfg(p_key))::integer $$;

create function private.cfg_text(p_key text)
returns text
language sql
stable
set search_path = ''
as $$ select private.cfg(p_key) #>> '{}' $$;

-- The game clock. A fake time (`set app.fake_now = '…'`) is honoured only for direct
-- database sessions (tests, jobs/replay.py), never for API requests, whose session user is
-- one of the API roles: players cannot move deadlines.
create function private.clock()
returns timestamptz
language plpgsql
stable
set search_path = ''
as $$
declare
  v_fake text := nullif(current_setting('app.fake_now', true), '');
begin
  if v_fake is not null
     and session_user not in ('authenticator', 'anon', 'authenticated', 'service_role') then
    return v_fake::timestamptz;
  end if;
  return now();
end;
$$;

-- Errors are stable codes + variables (JSON in DETAIL); the UI translates them.
create function private.raise_error(p_code text, p_vars jsonb default '{}'::jsonb)
returns void
language plpgsql
set search_path = ''
as $$
begin
  raise exception using message = p_code, detail = p_vars::text, errcode = 'P0001';
end;
$$;

-- Paris-local wall time on a given date, as UTC instant.
create function private.local_instant(p_date date, p_local_time text)
returns timestamptz
language sql
stable
set search_path = ''
as $$
  select (p_date + p_local_time::time) at time zone private.cfg_text('timezone')
$$;

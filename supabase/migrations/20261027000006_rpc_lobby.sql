-- Lobby RPCs (GAME_RULES §1). Errors: private.raise_error(code, vars).

create function private.require_user()
returns uuid
language plpgsql
stable
set search_path = ''
as $$
declare
  v_uid uuid := auth.uid();
begin
  if v_uid is null then
    perform private.raise_error('NOT_AUTHENTICATED');
  end if;
  return v_uid;
end;
$$;

create function private.lock_league(p_league uuid)
returns public.leagues
language plpgsql
security definer
set search_path = ''
as $$
declare
  v_league public.leagues;
begin
  select * into v_league from public.leagues l where l.id = p_league for update;
  if not found then
    perform private.raise_error('LEAGUE_NOT_FOUND');
  end if;
  return v_league;
end;
$$;

create function private.require_member(p_league uuid)
returns public.league_members
language plpgsql
security definer
set search_path = ''
as $$
declare
  v_member public.league_members;
begin
  select * into v_member from public.league_members m
  where m.league_id = p_league and m.user_id = private.require_user();
  if not found then
    perform private.raise_error('NOT_A_MEMBER');
  end if;
  return v_member;
end;
$$;

-- Returns the trimmed pseudo or raises.
create function private.validate_member_fields(
  p_league uuid,
  p_pseudo text,
  p_commander public.commander,
  p_avatar_color text,
  p_exclude_member uuid
)
returns text
language plpgsql
security definer
set search_path = ''
as $$
declare
  v_pseudo text := btrim(coalesce(p_pseudo, ''));
  v_min integer := private.cfg_int('pseudo_min_length');
  v_max integer := private.cfg_int('pseudo_max_length');
begin
  if char_length(v_pseudo) < v_min or char_length(v_pseudo) > v_max then
    perform private.raise_error('PSEUDO_LENGTH', jsonb_build_object('min', v_min, 'max', v_max));
  end if;
  if v_pseudo !~ '^[[:print:]]+$' then
    perform private.raise_error('PSEUDO_INVALID');
  end if;
  if lower(v_pseudo) = 'drone' then
    perform private.raise_error('PSEUDO_RESERVED');
  end if;
  if exists (
    select 1 from public.league_members m
    where m.league_id = p_league and lower(m.pseudo) = lower(v_pseudo)
      and m.member_id is distinct from p_exclude_member
  ) then
    perform private.raise_error('PSEUDO_TAKEN');
  end if;
  if p_commander is null then
    perform private.raise_error('COMMANDER_REQUIRED');
  end if;
  if not (private.cfg('avatar_colors') ? coalesce(p_avatar_color, '')) then
    perform private.raise_error('AVATAR_COLOR_INVALID');
  end if;
  return v_pseudo;
end;
$$;

create function private.new_invite_code()
returns text
language plpgsql
volatile
security definer
set search_path = ''
as $$
declare
  v_alphabet text := private.cfg_text('invite_code_alphabet');
  v_length integer := private.cfg_int('invite_code_length');
  v_code text;
  v_bytes bytea;
begin
  loop
    v_code := '';
    v_bytes := uuid_send(gen_random_uuid()) || uuid_send(gen_random_uuid());
    for i in 0 .. v_length - 1 loop
      v_code := v_code || substr(
        v_alphabet, 1 + (get_byte(v_bytes, i) % char_length(v_alphabet)), 1
      );
    end loop;
    exit when not exists (select 1 from public.leagues l where l.invite_code = v_code);
  end loop;
  return v_code;
end;
$$;

-- The Monday of week 1: the first week whose lock is at least min_first_briefing_hours away.
create function private.first_week_monday(p_now timestamptz)
returns date
language plpgsql
stable
set search_path = ''
as $$
declare
  v_today date := (p_now at time zone private.cfg_text('timezone'))::date;
  v_monday date := v_today + (8 - extract(isodow from v_today)::integer);
begin
  if private.local_instant(v_monday - 1, private.cfg_text('lock_local_time'))
     < p_now + make_interval(hours => private.cfg_int('min_first_briefing_hours')) then
    v_monday := v_monday + 7;
  end if;
  return v_monday;
end;
$$;

create function public.create_league(
  p_name text,
  p_max_players integer,
  p_campaign_weeks integer,
  p_drone_enabled boolean,
  p_pseudo text,
  p_commander public.commander,
  p_avatar_color text
)
returns uuid
language plpgsql
security definer
set search_path = ''
as $$
declare
  v_uid uuid := private.require_user();
  v_name text := btrim(coalesce(p_name, ''));
  v_name_max integer := private.cfg_int('league_name_max_length');
  v_league uuid := gen_random_uuid();
  v_pseudo text;
begin
  if char_length(v_name) < 1 or char_length(v_name) > v_name_max then
    perform private.raise_error('LEAGUE_NAME_LENGTH', jsonb_build_object('max', v_name_max));
  end if;
  if p_max_players is null
     or p_max_players < private.cfg_int('min_players')
     or p_max_players > private.cfg_int('max_players') then
    perform private.raise_error('MAX_PLAYERS_RANGE', jsonb_build_object(
      'min', private.cfg_int('min_players'), 'max', private.cfg_int('max_players')));
  end if;
  if p_campaign_weeks is null
     or p_campaign_weeks < private.cfg_int('campaign_weeks_min')
     or p_campaign_weeks > private.cfg_int('campaign_weeks_max') then
    perform private.raise_error('CAMPAIGN_WEEKS_RANGE', jsonb_build_object(
      'min', private.cfg_int('campaign_weeks_min'), 'max', private.cfg_int('campaign_weeks_max')));
  end if;
  v_pseudo := private.validate_member_fields(v_league, p_pseudo, p_commander, p_avatar_color, null);

  insert into public.leagues (id, name, invite_code, host_id, max_players, campaign_weeks,
                              drone_enabled)
  values (v_league, v_name, private.new_invite_code(), v_uid, p_max_players, p_campaign_weeks,
          coalesce(p_drone_enabled, true));
  insert into public.league_members (league_id, user_id, pseudo, commander, avatar_color)
  values (v_league, v_uid, v_pseudo, p_commander, p_avatar_color);
  return v_league;
end;
$$;

create function public.join_league(
  p_code text,
  p_pseudo text,
  p_commander public.commander,
  p_avatar_color text
)
returns uuid
language plpgsql
security definer
set search_path = ''
as $$
declare
  v_uid uuid := private.require_user();
  v_league_id uuid;
  v_league public.leagues;
  v_pseudo text;
begin
  select l.id into v_league_id from public.leagues l
  where l.invite_code = upper(btrim(coalesce(p_code, '')));
  if v_league_id is null then
    perform private.raise_error('LEAGUE_NOT_FOUND');
  end if;
  v_league := private.lock_league(v_league_id);
  if v_league.status <> 'lobby' then
    perform private.raise_error('LEAGUE_NOT_IN_LOBBY');
  end if;
  if exists (select 1 from public.league_members m
             where m.league_id = v_league.id and m.user_id = v_uid) then
    perform private.raise_error('ALREADY_MEMBER');
  end if;
  if (select count(*) from public.league_members m
      where m.league_id = v_league.id and not m.is_drone) >= v_league.max_players then
    perform private.raise_error('LEAGUE_FULL', jsonb_build_object('max', v_league.max_players));
  end if;
  v_pseudo := private.validate_member_fields(v_league.id, p_pseudo, p_commander, p_avatar_color, null);
  insert into public.league_members (league_id, user_id, pseudo, commander, avatar_color)
  values (v_league.id, v_uid, v_pseudo, p_commander, p_avatar_color);
  return v_league.id;
end;
$$;

-- Lobby only. When the host leaves, the earliest other member becomes host; a league left
-- empty is deleted.
create function public.leave_league(p_league uuid)
returns void
language plpgsql
security definer
set search_path = ''
as $$
declare
  v_member public.league_members := private.require_member(p_league);
  v_league public.leagues := private.lock_league(p_league);
  v_next uuid;
begin
  if v_league.status <> 'lobby' then
    perform private.raise_error('LEAGUE_NOT_IN_LOBBY');
  end if;
  delete from public.league_members m where m.member_id = v_member.member_id;
  if v_league.host_id = v_member.user_id then
    select m.user_id into v_next from public.league_members m
    where m.league_id = p_league and not m.is_drone
    order by m.joined_at, m.member_id
    limit 1;
    if v_next is null then
      delete from public.leagues l where l.id = p_league;
    else
      update public.leagues l set host_id = v_next where l.id = p_league;
    end if;
  end if;
end;
$$;

create function public.update_member(
  p_league uuid,
  p_pseudo text,
  p_commander public.commander,
  p_avatar_color text
)
returns void
language plpgsql
security definer
set search_path = ''
as $$
declare
  v_member public.league_members := private.require_member(p_league);
  v_league public.leagues := private.lock_league(p_league);
  v_pseudo text;
begin
  if v_league.status <> 'lobby' then
    perform private.raise_error('LEAGUE_NOT_IN_LOBBY');
  end if;
  v_pseudo := private.validate_member_fields(
    p_league, p_pseudo, p_commander, p_avatar_color, v_member.member_id);
  update public.league_members m
  set pseudo = v_pseudo, commander = p_commander, avatar_color = p_avatar_color
  where m.member_id = v_member.member_id;
end;
$$;

create function public.set_ready(p_league uuid, p_ready boolean)
returns void
language plpgsql
security definer
set search_path = ''
as $$
declare
  v_member public.league_members := private.require_member(p_league);
  v_league public.leagues := private.lock_league(p_league);
begin
  if v_league.status <> 'lobby' then
    perform private.raise_error('LEAGUE_NOT_IN_LOBBY');
  end if;
  update public.league_members m set ready = coalesce(p_ready, false)
  where m.member_id = v_member.member_id;
end;
$$;

-- Host only, at least min_players humans ready. Every member plays, ready or not (members
-- who are not ready get an auto squad if they do not draft). Creates the Drone and week 1.
create function public.start_campaign(p_league uuid)
returns date
language plpgsql
security definer
set search_path = ''
as $$
declare
  v_member public.league_members := private.require_member(p_league);
  v_league public.leagues := private.lock_league(p_league);
  v_ready integer;
  v_min integer := private.cfg_int('min_players');
  v_now timestamptz := private.clock();
  v_monday date;
  v_colors jsonb := private.cfg('avatar_colors');
begin
  if v_league.host_id <> v_member.user_id then
    perform private.raise_error('NOT_HOST');
  end if;
  if v_league.status <> 'lobby' then
    perform private.raise_error('LEAGUE_NOT_IN_LOBBY');
  end if;
  select count(*) into v_ready from public.league_members m
  where m.league_id = p_league and not m.is_drone and m.ready;
  if v_ready < v_min then
    perform private.raise_error('NOT_ENOUGH_READY', jsonb_build_object('ready', v_ready, 'min', v_min));
  end if;

  v_monday := private.first_week_monday(v_now);
  if v_league.drone_enabled then
    insert into public.league_members (league_id, user_id, pseudo, commander, avatar_color,
                                       ready, is_drone)
    values (p_league, null, 'Drone', null, v_colors ->> (jsonb_array_length(v_colors) - 1),
            true, true);
  end if;
  insert into public.weeks (league_id, week, number, phase, is_final, lock_at,
                            resupply_closes_at, phase_changed_at)
  values (
    p_league, v_monday, 1, 'briefing', v_league.campaign_weeks = 1,
    private.local_instant(v_monday - 1, private.cfg_text('lock_local_time')),
    private.local_instant(v_monday + 3, private.cfg_text('resupply_close_local_time')),
    v_now
  );
  update public.leagues l
  set status = 'active', start_week = v_monday, started_at = v_now
  where l.id = p_league;
  return v_monday;
end;
$$;

create function public.set_locale(p_locale public.locale)
returns void
language plpgsql
security definer
set search_path = ''
as $$
declare
  v_uid uuid := private.require_user();
begin
  if p_locale is null then
    perform private.raise_error('LOCALE_INVALID');
  end if;
  insert into public.profiles (id, locale) values (v_uid, p_locale)
  on conflict (id) do update set locale = excluded.locale;
end;
$$;

-- Player RPCs: authenticated only (never anon).
revoke execute on function
  public.create_league(text, integer, integer, boolean, text, public.commander, text),
  public.join_league(text, text, public.commander, text),
  public.leave_league(uuid),
  public.update_member(uuid, text, public.commander, text),
  public.set_ready(uuid, boolean),
  public.start_campaign(uuid),
  public.set_locale(public.locale)
from public, anon;
grant execute on function
  public.create_league(text, integer, integer, boolean, text, public.commander, text),
  public.join_league(text, text, public.commander, text),
  public.leave_league(uuid),
  public.update_member(uuid, text, public.commander, text),
  public.set_ready(uuid, boolean),
  public.start_campaign(uuid),
  public.set_locale(public.locale)
to authenticated;

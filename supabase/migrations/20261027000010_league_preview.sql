-- Join page preview (milestone 05): what a player holding an invite code may see before
-- joining. Read-only; reveals nothing beyond what the code already gives access to (the
-- league name, its state, the host's pseudo and the seats taken). Unknown code: the same
-- LEAGUE_NOT_FOUND error as join_league.
create function public.league_preview(p_code text)
returns table (
  league_id uuid,
  name text,
  status public.league_status,
  host_pseudo text,
  players integer,
  max_players integer,
  is_member boolean
)
language plpgsql
stable
security definer
set search_path = ''
as $$
declare
  v_uid uuid := private.require_user();
  v_league public.leagues;
begin
  select l.* into v_league from public.leagues l
  where l.invite_code = upper(btrim(coalesce(p_code, '')));
  if v_league.id is null then
    perform private.raise_error('LEAGUE_NOT_FOUND');
  end if;
  return query
  select
    v_league.id,
    v_league.name,
    v_league.status,
    (select m.pseudo from public.league_members m
     where m.league_id = v_league.id and m.user_id = v_league.host_id),
    (select count(*)::integer from public.league_members m
     where m.league_id = v_league.id and not m.is_drone),
    v_league.max_players,
    exists (select 1 from public.league_members m
            where m.league_id = v_league.id and m.user_id = v_uid);
end;
$$;

revoke execute on function public.league_preview(text) from public, anon;
grant execute on function public.league_preview(text) to authenticated;

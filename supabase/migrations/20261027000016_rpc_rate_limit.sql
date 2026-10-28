-- Milestone 09: per-user rate limit on the player RPCs that write.
--
-- PostgREST calls private.check_request() before every API request (db-pre-request, set
-- on the authenticator role below), inside the request's transaction and as the request's
-- role. It counts the user's RPC calls in the current minute and refuses the call with
-- RATE_LIMITED past `rpc_rate_limit_per_minute` (engine/config.py).
--
-- What is counted: POST /rpc/* of a logged-in user in a read-write transaction, i.e. the
-- volatile RPCs (PostgREST runs stable ones, such as server_time or order_costs, read-only).
-- A call that the RPC itself refuses rolls back with its count (Postgres has no autonomous
-- transaction): refused calls write nothing and fail fast; the platform's API limits cover
-- raw floods. Once over the limit, every call of that minute is refused, since the refusal
-- rolls back the increment that crossed it.

create table private.rpc_calls (
  user_id uuid not null,
  minute timestamptz not null,
  calls integer not null,
  primary key (user_id, minute)
);
alter table private.rpc_calls enable row level security;  -- no policy: only the hook writes

create function private.check_request()
returns void
language plpgsql
security definer
set search_path = ''
as $$
declare
  v_uid uuid := auth.uid();
  v_minute timestamptz := date_trunc('minute', now());
  v_limit integer;
  v_calls integer;
begin
  if v_uid is null
     or coalesce(current_setting('request.path', true), '') not like '/rpc/%'
     or current_setting('transaction_read_only') = 'on' then
    return;
  end if;
  v_limit := private.cfg_int('rpc_rate_limit_per_minute');
  delete from private.rpc_calls c where c.user_id = v_uid and c.minute < v_minute;
  insert into private.rpc_calls as c (user_id, minute, calls)
  values (v_uid, v_minute, 1)
  on conflict (user_id, minute) do update set calls = c.calls + 1
  returning c.calls into v_calls;
  if v_calls > v_limit then
    perform private.raise_error('RATE_LIMITED', jsonb_build_object('limit', v_limit));
  end if;
end;
$$;

-- PostgREST runs the hook as anon too (it returns at once: no user).
grant usage on schema private to anon;
grant execute on function private.check_request() to anon, authenticated, service_role;

alter role authenticator set pgrst.db_pre_request = 'private.check_request';
notify pgrst, 'reload config';

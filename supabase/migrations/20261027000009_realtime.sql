-- Realtime: clients subscribe only to these tables (never views), each protected by RLS.
alter publication supabase_realtime add table
  public.scores_live_public,
  public.events,
  public.league_members,
  public.weeks,
  public.pacts;

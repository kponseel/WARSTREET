-- The profile's language starts as the browser language sent at sign-up
-- (signInWithOtp options.data.locale), instead of always 'en' (CLAUDE.md: language =
-- profiles.locale, defaulting to the browser language). Anything else falls back to 'en'.
create or replace function private.handle_new_user()
returns trigger
language plpgsql
security definer
set search_path = ''
as $$
declare
  v_locale text := new.raw_user_meta_data ->> 'locale';
begin
  insert into public.profiles (id, locale)
  values (
    new.id,
    case when v_locale in ('en', 'fr') then v_locale::public.locale else 'en'::public.locale end
  )
  on conflict (id) do nothing;
  return new;
end;
$$;

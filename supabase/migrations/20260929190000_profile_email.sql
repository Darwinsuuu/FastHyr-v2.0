-- WS-003 Manage members: the members list shows each member's email, which Supabase Auth keeps
-- in auth.users. The API has no access to the auth schema, so profiles carries a copy that
-- these triggers keep current on sign-up and on email change.

alter table public.profiles add column email text;

update public.profiles p
set email = lower(u.email)
from auth.users u
where u.id = p.id;

create or replace function public.handle_new_user() returns trigger
language plpgsql
security definer
set search_path = ''
as $$
begin
  insert into public.profiles (id, full_name, avatar_url, email)
  values (
    new.id,
    coalesce(new.raw_user_meta_data ->> 'full_name', new.raw_user_meta_data ->> 'name'),
    coalesce(new.raw_user_meta_data ->> 'avatar_url', new.raw_user_meta_data ->> 'picture'),
    lower(new.email)
  );
  return new;
end;
$$;

create function public.handle_user_email_change() returns trigger
language plpgsql
security definer
set search_path = ''
as $$
begin
  update public.profiles set email = lower(new.email) where id = new.id;
  return new;
end;
$$;

revoke all on function public.handle_user_email_change() from anon, authenticated, public;

create trigger on_auth_user_email_changed
  after update of email on auth.users
  for each row
  when (new.email is distinct from old.email)
  execute function public.handle_user_email_change();

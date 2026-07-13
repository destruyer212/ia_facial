-- v9: autenticacion del panel y membresias multiempresa.
-- Ejecutar despues de v8_multitenant_organizations.sql.

create table if not exists public.app_users (
  user_id uuid primary key default gen_random_uuid(),
  email text not null unique,
  full_name text,
  password_hash text not null,
  is_active boolean not null default true,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  last_login_at timestamptz
);

create table if not exists public.app_user_memberships (
  user_id uuid not null references public.app_users(user_id) on delete cascade,
  org_id uuid not null references public.organizations(org_id) on delete cascade,
  role text not null default 'operator',
  is_active boolean not null default true,
  created_at timestamptz not null default now(),
  primary key (user_id, org_id),
  constraint app_user_memberships_role_chk
    check (role in ('platform_admin', 'org_admin', 'operator', 'viewer'))
);

create unique index if not exists app_users_email_lower_uq
  on public.app_users (lower(email));

create index if not exists app_user_memberships_org_idx
  on public.app_user_memberships (org_id, is_active);

drop trigger if exists trg_app_users_touch_updated_at on public.app_users;
create trigger trg_app_users_touch_updated_at
before update on public.app_users
for each row execute function public.touch_updated_at();

alter table public.app_users enable row level security;
alter table public.app_user_memberships enable row level security;

drop policy if exists app_users_self_policy on public.app_users;
create policy app_users_self_policy on public.app_users
for all
using (
  user_id::text = coalesce(auth.jwt() ->> 'sub', '')
  or coalesce(auth.jwt() ->> 'app.role', '') = 'platform_admin'
)
with check (
  user_id::text = coalesce(auth.jwt() ->> 'sub', '')
  or coalesce(auth.jwt() ->> 'app.role', '') = 'platform_admin'
);

drop policy if exists app_user_memberships_org_policy on public.app_user_memberships;
create policy app_user_memberships_org_policy on public.app_user_memberships
for all
using (
  org_id::text = coalesce(auth.jwt() ->> 'app.org_id', '')
  or coalesce(auth.jwt() ->> 'app.role', '') = 'platform_admin'
)
with check (
  org_id::text = coalesce(auth.jwt() ->> 'app.org_id', '')
  or coalesce(auth.jwt() ->> 'app.role', '') = 'platform_admin'
);

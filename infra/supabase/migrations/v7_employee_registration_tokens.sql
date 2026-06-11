-- v7: pre-registro masivo de trabajadores mediante token seguro

alter table public.persons
  add column if not exists dni text,
  add column if not exists shift_id text,
  add column if not exists registration_status text not null default 'PENDING_FACE_REGISTRATION',
  add column if not exists face_registered_at timestamptz;

create index if not exists persons_registration_status_idx
  on public.persons(org_id, registration_status);

create unique index if not exists persons_org_dni_uq
  on public.persons(org_id, dni)
  where dni is not null;

create table if not exists public.employee_registration_tokens (
  id uuid primary key default gen_random_uuid(),
  org_id uuid not null references public.organizations(org_id) on delete cascade,
  employee_id text not null references public.persons(person_id) on delete cascade,
  token_hash text not null unique,
  status text not null default 'TOKEN_SENT',
  expires_at timestamptz not null,
  used_at timestamptz,
  created_at timestamptz not null default now(),
  created_by text,
  sent_to_email text not null
);

create index if not exists employee_registration_tokens_employee_idx
  on public.employee_registration_tokens(org_id, employee_id, created_at desc);

create index if not exists employee_registration_tokens_status_idx
  on public.employee_registration_tokens(org_id, status, expires_at);

alter table public.employee_registration_tokens enable row level security;

drop policy if exists employee_registration_tokens_org_policy on public.employee_registration_tokens;
create policy employee_registration_tokens_org_policy on public.employee_registration_tokens
for all
using (org_id::text = coalesce(auth.jwt() ->> 'app.org_id', ''))
with check (org_id::text = coalesce(auth.jwt() ->> 'app.org_id', ''));

create table if not exists public.employee_registration_token_audit (
  id uuid primary key default gen_random_uuid(),
  org_id uuid not null references public.organizations(org_id) on delete cascade,
  employee_id text references public.persons(person_id) on delete set null,
  token_id uuid references public.employee_registration_tokens(id) on delete set null,
  action text not null,
  success boolean not null default false,
  source text not null default 'api',
  created_at timestamptz not null default now(),
  metadata jsonb not null default '{}'::jsonb
);

create index if not exists employee_registration_token_audit_employee_idx
  on public.employee_registration_token_audit(org_id, employee_id, created_at desc);

alter table public.employee_registration_token_audit enable row level security;

drop policy if exists employee_registration_token_audit_org_policy on public.employee_registration_token_audit;
create policy employee_registration_token_audit_org_policy on public.employee_registration_token_audit
for all
using (org_id::text = coalesce(auth.jwt() ->> 'app.org_id', ''))
with check (org_id::text = coalesce(auth.jwt() ->> 'app.org_id', ''));

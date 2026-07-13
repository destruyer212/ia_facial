-- v8: empresas reales multi-tenant, perfil visual persistente y claves por organizacion.

alter table public.organizations
  add column if not exists ruc text,
  add column if not exists logo_url text,
  add column if not exists address text,
  add column if not exists brand_primary_color text not null default '#0d9488',
  add column if not exists brand_accent_color text not null default '#2563eb',
  add column if not exists brand_sidebar_color text not null default '#101827';

create table if not exists public.org_sites (
  org_id uuid not null references public.organizations(org_id) on delete cascade,
  site_code text not null,
  name text not null,
  address text,
  is_active boolean not null default true,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  primary key (org_id, site_code)
);

insert into public.org_sites (org_id, site_code, name, address, is_active)
select org_id, 'HQ', 'Oficina Principal', address, true
from public.organizations o
where not exists (
  select 1
  from public.org_sites s
  where s.org_id = o.org_id and s.site_code = 'HQ'
);

drop trigger if exists trg_org_sites_touch_updated_at on public.org_sites;
create trigger trg_org_sites_touch_updated_at
before update on public.org_sites
for each row execute function public.touch_updated_at();

alter table public.org_sites enable row level security;

drop policy if exists org_sites_org_policy on public.org_sites;
create policy org_sites_org_policy on public.org_sites
for all
using (org_id::text = coalesce(auth.jwt() ->> 'app.org_id', ''))
with check (org_id::text = coalesce(auth.jwt() ->> 'app.org_id', ''));

-- Las claves antiguas eran globales. Para SaaS real deben estar acotadas por org_id.
alter table public.face_assets drop constraint if exists face_assets_person_id_fkey;
alter table public.face_embeddings drop constraint if exists face_embeddings_person_id_fkey;
alter table public.attendance_events drop constraint if exists attendance_events_person_id_fkey;
alter table public.attendance_events drop constraint if exists attendance_events_device_id_fkey;
alter table public.attendance_incidents drop constraint if exists attendance_incidents_person_id_fkey;
alter table public.liveness_checks drop constraint if exists liveness_checks_person_id_fkey;
alter table public.person_shift_assignments drop constraint if exists person_shift_assignments_person_id_fkey;
alter table public.employee_registration_tokens drop constraint if exists employee_registration_tokens_employee_id_fkey;
alter table public.employee_registration_token_audit drop constraint if exists employee_registration_token_audit_employee_id_fkey;

alter table public.face_assets drop constraint if exists face_assets_person_org_fkey;
alter table public.face_embeddings drop constraint if exists face_embeddings_person_org_fkey;
alter table public.attendance_events drop constraint if exists attendance_events_person_org_fkey;
alter table public.attendance_events drop constraint if exists attendance_events_device_org_fkey;
alter table public.attendance_incidents drop constraint if exists attendance_incidents_person_org_fkey;
alter table public.liveness_checks drop constraint if exists liveness_checks_person_org_fkey;
alter table public.person_shift_assignments drop constraint if exists person_shift_assignments_person_org_fkey;
alter table public.employee_registration_tokens drop constraint if exists employee_registration_tokens_employee_org_fkey;
alter table public.employee_registration_token_audit drop constraint if exists employee_registration_token_audit_employee_org_fkey;

alter table public.persons drop constraint if exists persons_pkey;
alter table public.persons add constraint persons_pkey primary key (org_id, person_id);

alter table public.devices drop constraint if exists devices_pkey;
alter table public.devices add constraint devices_pkey primary key (org_id, device_id);

alter table public.face_assets
  add constraint face_assets_person_org_fkey
  foreign key (org_id, person_id)
  references public.persons(org_id, person_id)
  on delete cascade;

alter table public.face_embeddings
  add constraint face_embeddings_person_org_fkey
  foreign key (org_id, person_id)
  references public.persons(org_id, person_id)
  on delete cascade;

alter table public.attendance_events
  add constraint attendance_events_person_org_fkey
  foreign key (org_id, person_id)
  references public.persons(org_id, person_id)
  on delete cascade;

alter table public.attendance_events
  add constraint attendance_events_device_org_fkey
  foreign key (org_id, device_id)
  references public.devices(org_id, device_id);

alter table public.attendance_incidents
  add constraint attendance_incidents_person_org_fkey
  foreign key (org_id, person_id)
  references public.persons(org_id, person_id)
  on delete cascade;

alter table public.liveness_checks
  add constraint liveness_checks_person_org_fkey
  foreign key (org_id, person_id)
  references public.persons(org_id, person_id)
  on delete cascade;

alter table public.person_shift_assignments
  add constraint person_shift_assignments_person_org_fkey
  foreign key (org_id, person_id)
  references public.persons(org_id, person_id)
  on delete cascade;

alter table public.employee_registration_tokens
  add constraint employee_registration_tokens_employee_org_fkey
  foreign key (org_id, employee_id)
  references public.persons(org_id, person_id)
  on delete cascade;

alter table public.employee_registration_token_audit
  add constraint employee_registration_token_audit_employee_org_fkey
  foreign key (org_id, employee_id)
  references public.persons(org_id, person_id)
  on delete cascade;

drop index if exists attendance_checkin_once_per_day_uq;
drop index if exists attendance_checkout_once_per_day_uq;

create unique index if not exists attendance_checkin_once_per_day_uq
  on public.attendance_events (org_id, person_id, captured_on)
  where event_type = 'check_in' and accepted = true;

create unique index if not exists attendance_checkout_once_per_day_uq
  on public.attendance_events (org_id, person_id, captured_on)
  where event_type = 'check_out' and accepted = true;

create index if not exists face_assets_org_person_idx
  on public.face_assets(org_id, person_id, created_at desc);

create index if not exists liveness_checks_org_person_idx
  on public.liveness_checks(org_id, person_id, created_at desc)
  where person_id is not null;

create or replace view public.vw_person_daily_attendance as
select
  p.org_id,
  p.person_id,
  p.full_name,
  max(e.captured_at) filter (where e.event_type = 'check_in' and e.accepted) as last_check_in_at,
  max(e.captured_at) filter (where e.event_type = 'check_out' and e.accepted) as last_check_out_at
from public.persons p
left join public.attendance_events e
  on e.org_id = p.org_id and e.person_id = p.person_id
group by p.org_id, p.person_id, p.full_name;

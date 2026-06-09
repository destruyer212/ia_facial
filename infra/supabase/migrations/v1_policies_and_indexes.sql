-- v1: endurecer reglas, unicidad por turno y politicas RLS.
-- Ejecutar despues de v0_init.sql.

-- Evitamos expresiones no IMMUTABLE sobre timestamptz en indices.
alter table public.attendance_events
  add column if not exists captured_on date;

update public.attendance_events
set captured_on = (captured_at at time zone 'UTC')::date
where captured_on is null;

create or replace function public.set_attendance_captured_on()
returns trigger
language plpgsql
as $$
begin
  new.captured_on = (new.captured_at at time zone 'UTC')::date;
  return new;
end;
$$;

drop trigger if exists trg_attendance_set_captured_on on public.attendance_events;
create trigger trg_attendance_set_captured_on
before insert or update of captured_at on public.attendance_events
for each row
execute function public.set_attendance_captured_on();

-- Un solo check_in aceptado por persona/dia
create unique index if not exists attendance_checkin_once_per_day_uq
  on public.attendance_events (person_id, captured_on)
  where event_type = 'check_in' and accepted = true;

-- Un solo check_out aceptado por persona/dia
create unique index if not exists attendance_checkout_once_per_day_uq
  on public.attendance_events (person_id, captured_on)
  where event_type = 'check_out' and accepted = true;

-- HNSW index para similitud de embeddings (pgvector)
create index if not exists face_embeddings_hnsw_cosine_idx
  on public.face_embeddings
  using hnsw (embedding vector_cosine_ops);

-- RLS base (multiempresa por org_id; usar JWT claim app.org_id)
alter table public.organizations enable row level security;
alter table public.devices enable row level security;
alter table public.persons enable row level security;
alter table public.face_assets enable row level security;
alter table public.face_embeddings enable row level security;
alter table public.attendance_events enable row level security;
alter table public.attendance_incidents enable row level security;

drop policy if exists org_select_policy on public.organizations;
create policy org_select_policy on public.organizations
for select
using (
  org_id::text = coalesce(auth.jwt() ->> 'app.org_id', '')
);

drop policy if exists org_write_policy on public.organizations;
create policy org_write_policy on public.organizations
for all
using (
  org_id::text = coalesce(auth.jwt() ->> 'app.org_id', '')
)
with check (
  org_id::text = coalesce(auth.jwt() ->> 'app.org_id', '')
);

-- Policies helper: aplica misma regla por org_id a tablas hijas.
drop policy if exists devices_org_policy on public.devices;
create policy devices_org_policy on public.devices
for all
using (org_id::text = coalesce(auth.jwt() ->> 'app.org_id', ''))
with check (org_id::text = coalesce(auth.jwt() ->> 'app.org_id', ''));

drop policy if exists persons_org_policy on public.persons;
create policy persons_org_policy on public.persons
for all
using (org_id::text = coalesce(auth.jwt() ->> 'app.org_id', ''))
with check (org_id::text = coalesce(auth.jwt() ->> 'app.org_id', ''));

drop policy if exists face_assets_org_policy on public.face_assets;
create policy face_assets_org_policy on public.face_assets
for all
using (org_id::text = coalesce(auth.jwt() ->> 'app.org_id', ''))
with check (org_id::text = coalesce(auth.jwt() ->> 'app.org_id', ''));

drop policy if exists face_embeddings_org_policy on public.face_embeddings;
create policy face_embeddings_org_policy on public.face_embeddings
for all
using (org_id::text = coalesce(auth.jwt() ->> 'app.org_id', ''))
with check (org_id::text = coalesce(auth.jwt() ->> 'app.org_id', ''));

drop policy if exists attendance_events_org_policy on public.attendance_events;
create policy attendance_events_org_policy on public.attendance_events
for all
using (org_id::text = coalesce(auth.jwt() ->> 'app.org_id', ''))
with check (org_id::text = coalesce(auth.jwt() ->> 'app.org_id', ''));

drop policy if exists attendance_incidents_org_policy on public.attendance_incidents;
create policy attendance_incidents_org_policy on public.attendance_incidents
for all
using (org_id::text = coalesce(auth.jwt() ->> 'app.org_id', ''))
with check (org_id::text = coalesce(auth.jwt() ->> 'app.org_id', ''));

-- Vista util para dashboard: ultimo estado por persona en el dia
create or replace view public.vw_person_daily_attendance as
select
  p.org_id,
  p.person_id,
  p.full_name,
  max(e.captured_at) filter (where e.event_type = 'check_in' and e.accepted) as last_check_in_at,
  max(e.captured_at) filter (where e.event_type = 'check_out' and e.accepted) as last_check_out_at
from public.persons p
left join public.attendance_events e on e.person_id = p.person_id
group by p.org_id, p.person_id, p.full_name;

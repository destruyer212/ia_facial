-- v0: esquema base para IA Facial sobre Supabase (Postgres + pgvector)
-- Ejecutar primero este archivo.

create extension if not exists pgcrypto;
create extension if not exists vector;

create table if not exists public.organizations (
  org_id uuid primary key default gen_random_uuid(),
  code text not null unique,
  name text not null,
  timezone text not null default 'America/Lima',
  is_active boolean not null default true,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists public.devices (
  device_id text primary key,
  org_id uuid not null references public.organizations(org_id) on delete cascade,
  label text not null,
  kind text not null default 'edge',
  location text,
  is_active boolean not null default true,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists public.persons (
  person_id text primary key,
  org_id uuid not null references public.organizations(org_id) on delete cascade,
  employee_code text,
  full_name text not null,
  email text,
  is_active boolean not null default true,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create unique index if not exists persons_org_employee_code_uq
  on public.persons(org_id, employee_code)
  where employee_code is not null;

create table if not exists public.face_assets (
  face_asset_id uuid primary key default gen_random_uuid(),
  org_id uuid not null references public.organizations(org_id) on delete cascade,
  person_id text not null references public.persons(person_id) on delete cascade,
  provider text not null default 'cloudflare_r2',
  r2_key text not null unique,
  public_url text,
  content_type text not null default 'image/jpeg',
  checksum_sha256 text,
  bytes_size bigint,
  captured_at timestamptz,
  created_at timestamptz not null default now()
);

create index if not exists face_assets_person_idx on public.face_assets(person_id, created_at desc);

create table if not exists public.face_embeddings (
  embedding_id uuid primary key default gen_random_uuid(),
  org_id uuid not null references public.organizations(org_id) on delete cascade,
  person_id text not null references public.persons(person_id) on delete cascade,
  model text not null,
  embedding vector(512) not null,
  threshold real not null default 0.35,
  face_asset_id uuid references public.face_assets(face_asset_id) on delete set null,
  metadata jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create index if not exists face_embeddings_org_model_idx
  on public.face_embeddings(org_id, model, created_at desc);

create table if not exists public.attendance_events (
  event_id text primary key,
  org_id uuid not null references public.organizations(org_id) on delete cascade,
  person_id text not null references public.persons(person_id) on delete cascade,
  employee_name text,
  device_id text not null references public.devices(device_id),
  event_type text not null check (event_type in ('check_in', 'check_out')),
  confidence real not null check (confidence >= 0 and confidence <= 1),
  captured_at timestamptz not null,
  source text not null default 'edge',
  evidence_ref text,
  accepted boolean not null default true,
  duplicate boolean not null default false,
  created_at timestamptz not null default now()
);

create index if not exists attendance_events_person_time_idx
  on public.attendance_events(person_id, captured_at desc);
create index if not exists attendance_events_org_time_idx
  on public.attendance_events(org_id, captured_at desc);

create table if not exists public.attendance_incidents (
  incident_id text primary key,
  org_id uuid not null references public.organizations(org_id) on delete cascade,
  person_id text not null references public.persons(person_id) on delete cascade,
  employee_name text,
  violation_type text not null,
  attempted_at timestamptz not null,
  scheduled_exit_time time not null,
  tolerance_minutes int not null,
  minutes_early int not null,
  reason text,
  analysis jsonb,
  severity text not null,
  status text not null default 'open',
  evidence_ref text,
  supervisor_notified boolean not null default false,
  created_at timestamptz not null default now()
);

create index if not exists attendance_incidents_person_time_idx
  on public.attendance_incidents(person_id, created_at desc);

create or replace function public.match_face_embeddings(
  in_org_id uuid,
  in_model text,
  in_embedding vector(512),
  in_threshold real default 0.35,
  in_match_count int default 1
)
returns table (
  person_id text,
  full_name text,
  model text,
  distance real,
  confidence real
)
language sql
stable
as $$
  select
    e.person_id,
    p.full_name,
    e.model,
    (e.embedding <=> in_embedding)::real as distance,
    greatest(0, least(1, 1 - (e.embedding <=> in_embedding)))::real as confidence
  from public.face_embeddings e
  join public.persons p on p.person_id = e.person_id
  where e.org_id = in_org_id
    and e.model = in_model
    and (e.embedding <=> in_embedding) <= in_threshold
  order by e.embedding <=> in_embedding
  limit greatest(1, in_match_count);
$$;

create or replace function public.touch_updated_at()
returns trigger
language plpgsql
as $$
begin
  new.updated_at = now();
  return new;
end;
$$;

drop trigger if exists trg_org_touch_updated_at on public.organizations;
create trigger trg_org_touch_updated_at
before update on public.organizations
for each row execute function public.touch_updated_at();

drop trigger if exists trg_devices_touch_updated_at on public.devices;
create trigger trg_devices_touch_updated_at
before update on public.devices
for each row execute function public.touch_updated_at();

drop trigger if exists trg_persons_touch_updated_at on public.persons;
create trigger trg_persons_touch_updated_at
before update on public.persons
for each row execute function public.touch_updated_at();

drop trigger if exists trg_embeddings_touch_updated_at on public.face_embeddings;
create trigger trg_embeddings_touch_updated_at
before update on public.face_embeddings
for each row execute function public.touch_updated_at();

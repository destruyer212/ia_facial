-- v2: auditoría de validaciones de vida (Fase 4)

create table if not exists public.liveness_checks (
  check_id uuid primary key default gen_random_uuid(),
  org_id uuid not null references public.organizations(org_id) on delete cascade,
  person_id text references public.persons(person_id) on delete set null,
  passed boolean not null,
  score real not null,
  method text not null default 'mediapipe_v2',
  challenge_id text,
  checks jsonb not null default '{}'::jsonb,
  evidence_ref text,
  created_at timestamptz not null default now()
);

create index if not exists liveness_checks_org_created_idx
  on public.liveness_checks(org_id, created_at desc);

create index if not exists liveness_checks_person_idx
  on public.liveness_checks(person_id, created_at desc)
  where person_id is not null;

alter table public.liveness_checks enable row level security;

drop policy if exists liveness_checks_org_policy on public.liveness_checks;
create policy liveness_checks_org_policy on public.liveness_checks
  for all
  using (org_id::text = coalesce(auth.jwt() ->> 'app.org_id', ''))
  with check (org_id::text = coalesce(auth.jwt() ->> 'app.org_id', ''));

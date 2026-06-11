-- v6: turnos laborales simples y asignacion por empleado

create table if not exists public.work_shifts (
  org_id uuid not null references public.organizations(org_id) on delete cascade,
  shift_code text not null,
  name text not null,
  start_time time not null,
  end_time time not null,
  work_hours int not null default 8,
  tolerance_minutes int not null default 10,
  is_active boolean not null default true,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  primary key (org_id, shift_code)
);

create table if not exists public.person_shift_assignments (
  org_id uuid not null references public.organizations(org_id) on delete cascade,
  person_id text not null references public.persons(person_id) on delete cascade,
  shift_code text not null,
  assigned_at timestamptz not null default now(),
  primary key (org_id, person_id),
  foreign key (org_id, shift_code)
    references public.work_shifts(org_id, shift_code)
    on delete restrict
);

alter table public.work_shifts enable row level security;
alter table public.person_shift_assignments enable row level security;

drop policy if exists work_shifts_org_policy on public.work_shifts;
create policy work_shifts_org_policy on public.work_shifts
for all
using (org_id::text = coalesce(auth.jwt() ->> 'app.org_id', ''))
with check (org_id::text = coalesce(auth.jwt() ->> 'app.org_id', ''));

drop policy if exists person_shift_assignments_org_policy on public.person_shift_assignments;
create policy person_shift_assignments_org_policy on public.person_shift_assignments
for all
using (org_id::text = coalesce(auth.jwt() ->> 'app.org_id', ''))
with check (org_id::text = coalesce(auth.jwt() ->> 'app.org_id', ''));

with org as (
  select org_id from public.organizations where code = 'demo' limit 1
)
insert into public.work_shifts (
  org_id, shift_code, name, start_time, end_time, work_hours, tolerance_minutes
)
select org.org_id, v.shift_code, v.name, v.start_time::time, v.end_time::time, 8, 10
from org
cross join (
  values
    ('TM', 'Turno Manana', '08:00', '16:00'),
    ('TT', 'Turno Tarde', '14:00', '22:00')
) as v(shift_code, name, start_time, end_time)
on conflict (org_id, shift_code) do update set
  name = excluded.name,
  start_time = excluded.start_time,
  end_time = excluded.end_time,
  work_hours = excluded.work_hours,
  tolerance_minutes = excluded.tolerance_minutes,
  updated_at = now();

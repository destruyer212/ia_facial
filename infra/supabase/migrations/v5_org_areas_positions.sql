-- v5: catálogo maestro de Áreas y Cargos + vínculo con personas

create table if not exists public.org_areas (
  org_id uuid not null references public.organizations(org_id) on delete cascade,
  area_code text not null,
  name text not null,
  sort_order int not null default 0,
  is_active boolean not null default true,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  primary key (org_id, area_code)
);

create table if not exists public.org_positions (
  org_id uuid not null references public.organizations(org_id) on delete cascade,
  area_code text not null,
  position_code text not null,
  name text not null,
  sort_order int not null default 0,
  is_active boolean not null default true,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  primary key (org_id, area_code, position_code),
  foreign key (org_id, area_code)
    references public.org_areas(org_id, area_code)
    on delete cascade
);

alter table public.persons
  add column if not exists area_code text,
  add column if not exists position_code text;

create index if not exists persons_area_position_idx
  on public.persons(org_id, area_code, position_code);

-- Seed catálogo para organización demo
with org as (
  select org_id from public.organizations where code = 'demo' limit 1
)
insert into public.org_areas (org_id, area_code, name, sort_order)
select org.org_id, v.area_code, v.name, v.sort_order
from org
cross join (
  values
    ('GG', 'Gerencia General', 1),
    ('AD', 'Administración', 2),
    ('FN', 'Finanzas', 3),
    ('VN', 'Ventas', 4),
    ('OP', 'Operaciones', 5),
    ('LG', 'Logística', 6),
    ('TI', 'Tecnología', 7),
    ('RH', 'Recursos Humanos', 8),
    ('MS', 'Mantenimiento y Servicios', 9)
) as v(area_code, name, sort_order)
on conflict (org_id, area_code) do update set
  name = excluded.name,
  sort_order = excluded.sort_order,
  updated_at = now();

with org as (
  select org_id from public.organizations where code = 'demo' limit 1
)
insert into public.org_positions (org_id, area_code, position_code, name, sort_order)
select org.org_id, v.area_code, v.position_code, v.name, v.sort_order
from org
cross join (
  values
    ('GG', 'GE', 'Gerente General', 1),
    ('GG', 'SG', 'Subgerente', 2),
    ('GG', 'AG', 'Asistente de Gerencia', 3),
    ('AD', 'AD', 'Administrador', 1),
    ('AD', 'AA', 'Auxiliar Administrativo', 2),
    ('AD', 'RC', 'Recepcionista', 3),
    ('AD', 'SE', 'Secretaria', 4),
    ('FN', 'JF', 'Jefe de Finanzas', 1),
    ('FN', 'CF', 'Contador', 2),
    ('FN', 'AF', 'Auxiliar de Finanzas', 3),
    ('FN', 'TC', 'Tesorero', 4),
    ('VN', 'JV', 'Jefe de Ventas', 1),
    ('VN', 'EV', 'Ejecutivo de Ventas', 2),
    ('VN', 'AC', 'Asesor Comercial', 3),
    ('VN', 'SV', 'Supervisor de Ventas', 4),
    ('OP', 'JO', 'Jefe de Operaciones', 1),
    ('OP', 'SO', 'Supervisor de Operaciones', 2),
    ('OP', 'OR', 'Operario', 3),
    ('OP', 'TE', 'Técnico de Operaciones', 4),
    ('LG', 'JL', 'Jefe de Logística', 1),
    ('LG', 'AL', 'Almacenero', 2),
    ('LG', 'CD', 'Conductor', 3),
    ('LG', 'DP', 'Despachador', 4),
    ('TI', 'JT', 'Jefe de TI', 1),
    ('TI', 'DS', 'Desarrollador de Software', 2),
    ('TI', 'SA', 'Soporte y Administrador de Sistemas', 3),
    ('TI', 'AN', 'Analista de TI', 4),
    ('RH', 'JR', 'Jefe de Recursos Humanos', 1),
    ('RH', 'AR', 'Asistente de RRHH', 2),
    ('RH', 'RE', 'Reclutador', 3),
    ('RH', 'CP', 'Coordinador de Personal', 4),
    ('MS', 'PL', 'Personal de Limpieza', 1),
    ('MS', 'PM', 'Personal de Mantenimiento', 2),
    ('MS', 'VG', 'Vigilante', 3),
    ('MS', 'JM', 'Jefe de Mantenimiento', 4)
) as v(area_code, position_code, name, sort_order)
on conflict (org_id, area_code, position_code) do update set
  name = excluded.name,
  sort_order = excluded.sort_order,
  updated_at = now();

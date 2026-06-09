-- Seed minimo para arrancar en v0/v1
-- Ajusta codigos segun tu empresa.

insert into public.organizations (code, name, timezone)
values ('demo', 'IA Facial Demo', 'America/Lima')
on conflict (code) do update set
  name = excluded.name,
  timezone = excluded.timezone;

with org as (
  select org_id from public.organizations where code = 'demo'
)
insert into public.devices (device_id, org_id, label, kind, location)
select 'dashboard-camera-001', org.org_id, 'Dashboard Camara', 'edge', 'Oficina Principal'
from org
on conflict (device_id) do update set
  label = excluded.label,
  location = excluded.location,
  updated_at = now();

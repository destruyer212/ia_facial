# Supabase + R2 (v0/v1)

Guia para dejar el proyecto listo con:
- Base de datos en Supabase (Postgres + pgvector)
- Imagenes en Cloudflare R2
- Versionado de esquema `v0` y `v1`

## 1) Variables de entorno

En `backend/.env` agrega:

```env
DATABASE_URL=postgresql+psycopg://postgres:<PASSWORD>@db.<PROJECT_REF>.supabase.co:5432/postgres
SUPABASE_URL=https://<PROJECT_REF>.supabase.co
SUPABASE_ANON_KEY=<ANON_KEY>
SUPABASE_SERVICE_ROLE_KEY=<SERVICE_ROLE_KEY>

R2_ACCOUNT_ID=<ACCOUNT_ID>
R2_ACCESS_KEY_ID=<ACCESS_KEY>
R2_SECRET_ACCESS_KEY=<SECRET_KEY>
R2_BUCKET=ia-facial-images
R2_PUBLIC_BASE_URL=https://pub-xxxxxxxxxxxxxxxx.r2.dev
```

## 2) Crear esquema base (v0)

Ejecuta en SQL Editor de Supabase:

1. `infra/supabase/migrations/v0_init.sql`
2. `infra/supabase/seed_v0.sql`

Con esto ya tienes:
- organizaciones, personas, dispositivos
- embeddings con `vector(512)`
- eventos e incidencias de asistencia
- funcion `match_face_embeddings(...)` para reconocimiento

## 3) Endurecer reglas (v1)

Ejecuta:

1. `infra/supabase/migrations/v1_policies_and_indexes.sql`

Esto agrega:
- unicidad por dia para `check_in` y `check_out`
- indice HNSW para busqueda vectorial
- RLS multiempresa por claim `app.org_id`
- vista `vw_person_daily_attendance`

## 4) Configurar bucket R2

Prerequisito: AWS CLI instalado y variables `R2_*` exportadas.

PowerShell:

```powershell
cd C:\SpringProjectsnew\ia_facial\infra\r2
.\setup-r2.ps1
```

El script crea bucket (si no existe) y aplica `cors.json`.

## 5) Convencion recomendada para llaves en R2

Usa esta estructura:

```text
org/<org_code>/person/<person_id>/raw/<yyyy>/<mm>/<dd>/<uuid>.jpg
```

Y guarda en `face_assets.r2_key` esa ruta exacta.

## 6) Flujo v0 -> v1

- `v0`: MVP funcional (registro + identificacion + asistencia)
- `v1`: controles de duplicado/turno, RLS, indices vectoriales

## 7) Siguiente paso recomendado en backend

Migrar los stores JSON (`embedding_store`, `attendance_event_store`, `incident_store`) a repositorios SQL:
- `SupabaseEmbeddingStore`
- `SupabaseAttendanceEventStore`
- `SupabaseIncidentStore`

Mantener un feature flag:

```env
STORAGE_BACKEND=json # o supabase
```

Asi puedes cambiar de local a cloud sin romper el MVP.

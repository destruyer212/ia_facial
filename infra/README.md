# Infra

Infraestructura local para evolucionar el MVP.

## Docker Compose local

Desde `C:\SpringProjectsnew\ia_facial\infra`:

```powershell
docker compose up --build
```

Servicios:

- Backend FastAPI: `http://127.0.0.1:8000`
- PostgreSQL + pgvector: `localhost:5432`

## Nota sobre DeepFace en Docker

La imagen puede tardar en construir porque DeepFace y TensorFlow son dependencias pesadas. Para el primer MVP en Windows, es mas rapido empezar con virtualenv local.

## Cloud inicial

Ver [docs/CLOUD.md](C:/SpringProjectsnew/ia_facial/docs/CLOUD.md).


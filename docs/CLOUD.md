# Cloud gratis o casi gratis

Estado revisado el 2026-05-25 con documentacion oficial:

- Railway tiene plan Free de USD 0/mes para experimentacion, con recursos gratuitos limitados. Documentacion: https://docs.railway.com/pricing
- Render permite web services gratis y Postgres gratis para pruebas, pero los servicios free se duermen tras inactividad y el filesystem es efimero. Documentacion: https://render.com/docs/free
- Render Postgres free tiene limite de 1 GB y expira a los 30 dias. Documentacion: https://render.com/docs/free

## Recomendacion CTO

Para este proyecto:

1. MVP local en Windows: gratis y mas controlado.
2. Demo cloud: Render free puede servir, pero no guardes embeddings en filesystem.
3. Railway free puede servir para experimentar, pero vigila credito/uso.
4. Produccion: usa plan pago pequeno o VPS barato cuando haya clientes reales.

## Que subir a cloud primero

- Backend Docker.
- PostgreSQL administrado.
- Variables de entorno.
- Logs.

## Que no subir todavia

- Fotos originales sin politica legal.
- JSON local con embeddings.
- Endpoints sin autenticacion.
- Servicios de reconocimiento expuestos publicamente sin rate limit.

## Render vs Railway

Render:

- Bueno para demos rapidas.
- Ojo con cold starts.
- Ojo con Postgres free temporal.

Railway:

- Experiencia simple para contenedores y Postgres.
- Gratis solo para experimentacion limitada.
- Mejor controlar gasto desde el inicio.


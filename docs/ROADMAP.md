# Roadmap profesional

## Fase 0 - Base tecnica

- Crear estructura de carpetas.
- Levantar FastAPI.
- Agregar OpenCV.
- Agregar DeepFace.
- Probar endpoints con Swagger.

Criterio de salida: API local identifica una persona registrada.

## Fase 1 - MVP escritorio

- Registro de personas.
- Identificacion por imagen.
- Edge Windows con cache local para reconocimiento rapido.
- Endpoint de eventos de asistencia desde dispositivo.
- Voz local de bienvenida.
- Validacion de salida laboral con horario configurable.
- Analisis inicial de motivos.
- Generacion local de incidencias.
- Storage local JSON.
- Logs basicos.
- Documentar umbral y latencia.
- Pruebas con 20 a 50 imagenes reales autorizadas.

Criterio de salida: demo repetible en Windows.

## Fase 2 - Persistencia profesional

- PostgreSQL.
- Migraciones Alembic.
- Tablas de organizaciones, usuarios, personas, embeddings y eventos.
- Tablas de horarios, turnos, asistencia, incidencias y alertas.
- pgvector para busqueda de similitud.
- Auditoria de intentos.

Criterio de salida: datos sobreviven reinicios y son consultables.

## Fase 3 - Seguridad

- Login JWT.
- Roles.
- Filtros por organizacion.
- Hash de passwords con Argon2 o bcrypt.
- Rate limiting.
- Validacion estricta de archivos.

Criterio de salida: cada usuario ve solo su empresa.

## Fase 4 - Android

- Flutter app.
- Captura de imagen.
- Evaluar inferencia local en tablet para no depender de subir frames.
- Registro facial.
- Identificacion.
- Manejo de errores y estados.
- Pruebas en emulador y celular fisico.

Criterio de salida: Android consume API local.

## Fase 5 - Cloud

- Dockerizar backend.
- Desplegar API.
- Base de datos PostgreSQL administrada.
- Variables de entorno.
- Logs y monitoreo.
- Backups.

Criterio de salida: API accesible por HTTPS.

## Fase 6 - SaaS empresarial

- Multiempresa.
- Planes y limites.
- Invitaciones de usuarios.
- Auditoria avanzada.
- Reportes.
- Panel administrativo.
- Politicas de retencion de datos.
- Reglas por empresa, sede, area, turno y empleado.

Criterio de salida: varias empresas operan aisladas.

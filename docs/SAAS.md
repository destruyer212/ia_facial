# Conversion a SaaS empresarial

## Modelo mental

Un SaaS empresarial no es solo "subir la API a internet". Es aislar empresas, controlar permisos, auditar acciones, medir consumo y operar con soporte.

## Entidades SaaS

- `organizations`: empresas clientes.
- `users`: usuarios que entran al sistema.
- `roles`: permisos por usuario.
- `people`: personas registradas para reconocimiento.
- `face_embeddings`: embeddings por persona.
- `recognition_events`: historial de intentos.
- `work_schedules`: reglas horarias por empresa, sede o turno.
- `attendance_events`: entradas, salidas, pausas e intentos.
- `workforce_incidents`: incidencias laborales generadas.
- `supervisor_alerts`: notificaciones.
- `behavior_snapshots`: resumen historico por empleado.
- `edge_devices`: camaras, tablets o kiosks registrados.
- `edge_sync_manifests`: versiones de cache y reglas por dispositivo.
- `plans`: limites por empresa.
- `api_keys`: integraciones empresariales.

## Multiempresa

Todas las tablas operativas deben tener `organization_id`. Cada consulta debe filtrar por organizacion. No dependas solo del frontend para ocultar datos.

## Planes

Plan inicial:

- Free local/demo: uso manual.
- Starter: pocas personas y pocos eventos.
- Business: mas personas, auditoria y soporte.
- Enterprise: SLA, SSO, retencion configurable y despliegue dedicado.

## Medicion

Mide:

- Cantidad de personas registradas.
- Identificaciones por mes.
- Latencia promedio.
- Falsos positivos reportados.
- Falsos negativos reportados.
- Uso por organizacion.

## Ruta tecnica

1. Agregar PostgreSQL.
2. Agregar autenticacion.
3. Agregar `organization_id`.
4. Mover embeddings a pgvector.
5. Agregar auditoria.
6. Agregar limites por plan.
7. Agregar panel web.
8. Agregar facturacion cuando exista traccion.

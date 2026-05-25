# Seguridad y privacidad

## Advertencia importante

Los embeddings faciales son datos biometricos. Aunque no sean una foto, siguen siendo sensibles. El MVP local puede usar JSON, pero produccion necesita controles serios.

## Buenas practicas

- Consentimiento explicito antes de registrar rostro.
- No guardar imagenes originales salvo que el negocio lo exija.
- Si se guardan imagenes, usar cifrado y retencion limitada.
- No devolver embeddings completos al frontend.
- Usar HTTPS en cloud.
- Validar tipo, tamano y contenido de archivos.
- Rate limiting para endpoints de reconocimiento.
- Logs sin datos biometricos crudos.
- Separar organizaciones por `organization_id`.
- Backups cifrados.
- Acceso por roles.
- Separar decisiones automaticas de sanciones disciplinarias: la IA debe recomendar y auditar, no sancionar sola.
- Registrar quien configuro reglas, horarios y tolerancias.

## Passwords

- Nunca texto plano.
- Usar Argon2 o bcrypt.
- Access token corto.
- Refresh token revocable.

## Errores comunes

- Guardar fotos en cualquier carpeta sin politica.
- Usar un unico umbral para todos los escenarios sin medir.
- No auditar falsos positivos.
- Probar solo con fotos perfectas.
- Permitir endpoints publicos en internet.
- Mezclar datos de varias empresas.
- Hardcodear horarios en Android en vez de resolverlos desde el backend.

## Umbrales

El umbral de similitud no es universal. Depende de modelo, calidad de imagen, iluminacion y riesgo del negocio.

Para control de acceso fisico, se prefiere menor falso positivo aunque haya mas falsos negativos. Para busqueda asistida, se puede aceptar un umbral menos estricto y confirmacion humana.

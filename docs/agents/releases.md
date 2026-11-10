# Versiones, releases y registro de despliegues

Una versión identifica código. Un despliegue registra dónde y cuándo se instaló.
Publicar una release no actualiza Odoo ni activa políticas reales.

## Preparar una entrega

1. Elegir el commit de `main` con CI aprobado y comprobar que el manifiesto identifica
   esa entrega con una versión nueva. Si falta el incremento, prepararlo en un PR;
   no reutilizar una versión para dos contenidos distintos.
2. Preparar notas: problema resuelto, comportamiento final, validación, migraciones,
   límites conocidos y procedimiento de recuperación. No adjuntar dumps ni datos privados.
3. Crear la release como borrador para revisar commit, versión y contenido. Publicarla
   y crear el tag solo cuando se autorice ese paso. Nunca mover una etiqueta publicada.
4. Preparar y autorizar aparte el paquete de instalación. Después de ejecutarlo,
   registrar comprobación efectiva del servicio y datos; no inferir éxito del merge.

## Registro mínimo por instalación

| Campo | Contenido |
|---|---|
| Entorno y fecha | Producción/staging; fecha y zona horaria |
| Versión y commit | Versión del manifiesto y SHA completo realmente instalado |
| Validación | CI, casos focalizados, regresión y QA pertinentes |
| Autorización | Alcance autorizado; sin secretos ni conversaciones privadas |
| Respaldo | Ubicación del backup de BD, filestore y código; no su contenido |
| Resultado | Servicio, integridad de datos y verificaciones posteriores |
| Activación | Políticas o integraciones activadas, o constancia de que siguen apagadas |
| Recuperación | Procedimiento probado y referencia a la evidencia, si se utilizó |

## Situación al 10 de noviembre de 2026

- Último despliegue productivo documentado: `19.0.25.6.0`, commit
  `40ce2feebe93b89c71b0b653704307b1fd5bef46`, instalado el 3 de noviembre de 2026.
- `main` avanzó a `dea4efb05c9ca911c24e37b61b60c6da86270cdc` con el PR #114.
  Su manifiesto conserva `19.0.25.6.0`: antes del siguiente despliegue de producto
  falta preparar una versión nueva. No etiquetar ese commit como la entrega ya instalada.
- GitHub no mostraba tags ni releases en la consulta inicial. Se preparó un borrador
  retrospectivo `v19.0.25.6.0` apuntando al commit productivo acreditado 40ce2fe.
  Permanece como borrador: no se publicó tag ni se instaló código. Una publicación
  posterior no cambia la fecha de instalación ni acredita otras instalaciones históricas.
- Esta actualización de documentación y controles de CI no requiere subir versión
  del módulo. No habilita ni autoriza el siguiente despliegue de producto.

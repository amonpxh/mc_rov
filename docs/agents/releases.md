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

## Automatización compatible con Odoo

Se utiliza Python estándar, GitHub CLI y el token efímero de Actions, sin PAT ni
servicio pagado. `.odoo-release.json` conserva versión, commit base y excepciones
históricas revisadas. No representa la versión instalada en producción.

- `feat:` incrementa Y; `fix:`, `perf:` y mejoras compatibles incrementan Z.
  `!` o `BREAKING CHANGE:` incrementan X. El prefijo `19.0` se conserva.
- Solo cuentan cambios de producto: modelos, vistas, datos, permisos, reportes,
  migraciones, controles de entrada y assets. Documentación y CI solos no generan entrega.
- El título histórico del PR #114 tiene una clasificación `feat` explícita por SHA.
  Un futuro commit de producto sin clasificación detiene el cálculo y requiere revisión.
- `scripts/ci/odoo_release.py --output plan.json` calcula sin escribir producto.
  `--apply` se reserva para un checkout limpio del mismo HEAD; solo modifica manifiesto,
  CHANGELOG y estado de entrega. No ejecuta el manifiesto ni modifica una base de datos.
- Tras CI aprobado de main, `releases.yml` mantiene `ci/release-odoo` como rama del bot
  y un PR borrador de entrega. Revisa el último estado de cada check y el SHA actual;
  no usa código de un PR externo para el job con permisos de escritura.
- La referencia del bot se actualiza con lease del SHA anterior. Si hay cambios humanos,
  un commit no reconocido o una rama huérfana sin PR, se detiene para revisar.
- Cuando el PR del bot aparece, GitHub puede pedir **Approve workflows to run**.
  Una persona con escritura aprueba esas ejecuciones desde el PR; no hace falta un PAT.
  Verificar CI y que el PR esté actualizado antes de autorizar su squash.
- El merge de entrega debe conservar el título `chore(release): 19.0.X.Y.Z` y tener
  como padre la base exacta del plan. Si está obsoleto, no se crea la release.
- Una vez aprobado CI del commit de entrega, se crea una release **borrador** apuntando
  a ese SHA, sin publicar el tag. Repetir no duplica una propuesta ni una release.
- Si se cierra deliberadamente el PR del bot, revisar su rama antes de volver a ejecutar;
  la automatización no interpreta ese cierre como permiso para reabrirlo.

Consultar el [estado vigente](../pendientes.md) para la última instalación acreditada y el trabajo pendiente.

[Comportamiento oficial del token y aprobación de workflows](https://docs.github.com/en/actions/how-tos/write-workflows/choose-when-workflows-run/trigger-a-workflow).

## Base productiva documentada al 10 de noviembre de 2026

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

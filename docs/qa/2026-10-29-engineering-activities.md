# Validación de seguimiento de Ingeniería — 2026-10-29

Versión de entrega: **19.0.25.5.0**. Base contrastada con `origin/main`:
`d6f5efe2cd57900f96a07b1b468be1f747ab376c`. Correcciones finales:
`67622aa`. El cambio está preparado en rama; esta evidencia no declara publicación,
merge ni instalación en producción.

## Comportamiento

Una política explícita por empresa genera pendientes propios para preparar y
aplicar cambios de ingeniería de productos ROV. El límite inicial es un aniversario
desde la creación del ECO, calculado en la zona horaria configurada. El 29 de febrero
pasa al 28 de febrero cuando corresponde. Cambiar de etapa, archivar o reabrir no
reinicia ese plazo.

Las aprobaciones y la aplicación del cambio siguen siendo operaciones nativas de
PLM. Sus recordatorios son independientes de los pendientes propios. Marcar una
actividad como hecha no aprueba ni aplica el cambio. Las reprogramaciones de los
pendientes seguidos requieren coordinación y motivo mediante Repartir actividades.

Pausar impide pendientes nuevos y permite cerrar los existentes por eventos reales.
Reactivar no reconstruye eventos anteriores. No se crean políticas, destinatarios
reales ni pendientes históricos al instalar. La automatización de Inventario pertenece
al siguiente plan y no se incluye en esta entrega.

## Verificación automática

- Suite nativa completa: **979/979**, cero fallos y cero errores. Se verificó cada
  nombre y su multiplicidad, no solamente el resumen final. Son los 870 contratos
  anteriores más 109 de Ingeniería.
- Una revisión independiente de toda la rama detectó tres hallazgos importantes.
  Cinco regresiones nuevas reprodujeron exactamente esos fallos con los 200 casos
  anteriores del subconjunto verdes. Las tres correcciones pasaron la suite979.
- Seis escenarios con dos conexiones y reintentos transaccionales: creación,
  entrega repetida del evento, aprobadores distintos, aplicación, archivo y
  reapertura. Pasaron con las fuentes corregidas, sin actividades huérfanas y con
  aniversario conservado. La creación simultánea son dos ECO distintos; la entrega
  repetida verifica la identidad del mismo ECO.
- Se comprobó el rechazo nativo de aplicar sin permiso de escritura del producto.
  Solo los usuarios ficticios de la copia recibieron después el rol nativo necesario
  para probar la aplicación; el producto no concede ese permiso automáticamente.
- Fuentes verificadas mediante huellas, pruebas temporales restauradas, stock,
  calendarios, aprobadores, configuraciones y PDFs protegidos durante los controles.

La evidencia nativa completa se conserva localmente en
`.tmp/engineering-activity-pilot/`, fuera de Git: GREEN
`20261029-115354-053`, concurrencia `20261029-120234-670` y registros de QA.
El cambio posterior de versión es exclusivamente metadato del manifiesto.

## Prueba práctica

Se usó una copia aislada de STAGING con su filestore, correo y cron apagados,
servidor temporal limitado a localhost y red externa bloqueada. Las cuentas
Taller y Supervisor pertenecían a una empresa y calendario ficticios propios.

- ECO0745: generación única, inicio de revisión sin cierre anticipado, aprobación
  obligatoria nativa, transición a aplicar y cierre por aplicación real. La actividad
  de aplicación mostró vencimiento 29 de octubre de 2027.
- ECO0746: archivo con motivo en historial, reapertura con un pendiente único;
  pausa permite cerrar preparación sin generar aplicación; reactivar no reconstruye
  el pendiente omitido. La UI relativa mostró 365 días antes y después del archivo
  del mismo día; la conservación exacta de fecha se comprobó en las pruebas nativas.
- ECO0747: un cambio nuevo después de reactivar volvió a generar preparación.
  Taller confirmó acceso y cerró manualmente su actividad; quedó el registro del
  actor y siguió disponible Comenzar revisión.

El recordatorio nativo de aprobación no se cierra por coincidencia de título. El
usuario lo completó por separado tras la aprobación y aplicación del caso principal.
Las pruebas de seguridad RPC y reprogramación son cobertura automática; no se
declara que se hayan repetido manualmente en navegador.

## Incidencias del instalador QA

Se corrigieron tres problemas de la herramienta temporal, sin cambiar el producto:
lectura de UTF-8 como cp1252 al calcular una huella, uso de APIs de Recordset sobre
Environment y neutralización que dejaba la copia sin administrador activo. La última
corrección mantiene solamente en la copia un administrador técnico con credenciales
aleatorias nuevas, no publicadas; no concede ese rol a Taller o Supervisor.

La creación nativa de empresas modifica pertenencias del usuario técnico y puede
activar una ubicación compartida. Por eso la prueba operativa se trasladó a la copia,
sin sustituir los hooks nativos ni alterar cuentas o configuración de STAGING.
Los intentos fallidos se conservaron; cada continuación exigió la misma copia
bloqueada, vacía de escenario QA y neutralizada.

## Cierre y límites

El cierre nativo confirmó servidor QA detenido, respaldo del historial y conexiones
de la copia bloqueadas. Se conservan la base y el filestore para auditoría. STAGING
permaneció activo. Las cuentas técnicas y QA de la copia no están disponibles a través
del servidor temporal cerrado.

Producción continúa en **19.0.25.4.1**. Antes de activar seguimiento real habrá que
seleccionar cuentas, asignar sus roles nativos y verificar la zona horaria. La entrega
no activa configuración real ni modifica los flujos existentes de otros procesos.

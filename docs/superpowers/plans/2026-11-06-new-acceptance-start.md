# Apertura de aceptación formal de equipo nuevo

Usuario confirmó2026-11-06: un intento conjunto de rendimiento y terreno; basta un
fallo real en cualquiera. Ejecutar inline con TDD y revisión independiente final.

## Evidencia y decisiones

Auditoría nativa20261106-120322-119 revalidada:7 modelos,144 fuentes/PID intactos,
READ ONLY/rollback. `_get_backorder_mo_vals` conserva production_group_id; split
reparte movimientos y series. FEN exige RND y TRN confirmadas/aprobadas, pero su
emisión no acredita primer resultado. Ciclo de recordatorios depende de política;
el nuevo registro formal debe funcionar con creación automática pausada.

Ruling: episodio explícito de unidad nueva por empresa+serie; conserva MO realmente
productora, producto y grupo nativo al inicio. Una división de MO no crea otro
episodio de la misma unidad. Un origen distinto/incompatible se rechaza, sin
reclasificar silenciosamente una serie ya aceptada. No soportar como nueva unidad
un desmontaje/refabricación de la misma serie sin una decisión empresarial separada.
No reconstruir intentos antiguos ni usar una serie solo programada como fabricada.

## Primer incremento (sin resultado ni UI todavía)

Servicio `mc.rov.new.acceptance.start_attempt(production_id, lot_id, rnd_id, trn_id)`:
IDs positivos guardados, usuario interno con permisos de escritura sobre MO, serie
y ambas revisiones; producto/empresa/series autorizados. MO done y salida principal
serializada positiva verificadas con `_produced_lots`, excluye subproductos.
Pruebas explícitas guardadas/borrador, tipos rendimiento/terreno, misma serie y sin
reparación. No seleccionar automáticamente pruebas recientes ni confirmadas antes
de iniciar el intento. Operación idempotente para la misma selección pendiente;
reemplazarla exige cerrar el intento por el flujo posterior, no un contexto RPC.

Modelos privados `mc.rov.new.acceptance.episode` y `.attempt`, sin ACL pública.
Ordinal por episodio, fuentes y configuración de ambas pruebas congeladas al inicio;
capacidad Python interna para escrituras, no token serializable. Impedir borrado y
cambios de identidad/alcance que invaliden un pendiente. Permitir responder valores.
Bloqueo determinista MO→serie→revisiones→episodio para evitar duplicados; revisar
concurrencia explícitamente antes de entregar el flujo completo.

## Pasos

1. RED30 contratos de apertura/privacidad/identidad y4 controles nativos; conservar
   los127 anteriores de captura/KPI =161 focalizados. Transporte temporal, backup,
   restauración y snapshot; sin producto nuevo hasta confirmar RED.
2. Implementación mínima de apertura y protección, GREEN161 exactos y rollback.
3. Incremento posterior de eventos: confirma fuente nativa, congela resultado por
   fase; un fallo cierra intento fallido aunque falte la otra. Ambos aprobados y
   flags explícitos permiten primer pase; unknown no se convierte en éxito.
4. Interfaz, KPI, regresión, carreras, QA aislado y revisión final antes de entrega.

Este primer incremento no debe presentarse como aceptación conjunta terminada;
no genera actividades, no emite FEN ni modifica QA cerrada/producción.

## Estado

RED161 aprobado20261106-121251-779:30 ausencias y131 controles verdes. GREEN161
aprobado20261106-123243-038, backupZHubzw,145 fuentes exactas; esquema sin ACL/historia
real, datos intactos, pruebas restauradas y STAGING activo. Primer intento jZ0VNp
aprobó tests/verificación pero recuperó por marcador de empaquetado incongruente;
generador corregido con reproducción local y control de igualdad print/grep/echo.
Producto/casos iguales. Apertura validada, no flujo completo ni UI todavía.

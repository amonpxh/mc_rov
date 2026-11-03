# Servicio autorizado de KPI Implementation Plan

**Goal:** Leer etapas de seis flujos respetando consulta de equipo, empresas y documentos.

**Architecture:** `mc.rov.work.kpi` AbstractModel; núcleo puro ya probado. Primero RED
con eventos nativos; después adaptador y GREEN. El tablero sigue en otro incremento.

**API:** `get_summary(date_from=False, date_to=False, process="all")`. Fechas ISO o
False, rango inclusivo por fecha local del cierre; False significa sin límite.
No acepta booleanos True, fechas inválidas ni rango invertido. Procesos:
repair/manufacturing/acceptance/quality/engineering/inventory/all.
Respuesta: `generated_at`, `period`, `processes` y `partial`. Cada proceso incluye
`key`, `available`, `metrics`; no devuelve IDs, registros ni nombres individuales.
No sumar porcentajes o medianas de procesos. La agregación total queda para un contrato posterior.

**Authorization:** usuario interno con `group_work_assignment_team`. Coordinar NO implica
consultar equipo; ningún grupo nuevo. `env.companies` valida contexto. Primero comprobar
lectura nativa del modelo/documentos por empresas activas; después consultar runs privados
solo para esos IDs. No usar gateways con escritura/FOR UPDATE. Mantener ACL privadas.
Sin permiso de modelo: disponibleFalse/metricsNone en all; selección explícita rechazada.
Reglas de registro que oculten algunos documentos filtran población sin revelar sus IDs.

**Normalization:** `_now()` privado para pruebas, UTC naive. Cierre/corte en zona capturada;
zona ausente o inválida produce cobertura desconocida, nunca la zona actual inferida del usuario.
Pendiente usa actividad actual autorizada y activa; sin ella conserva obligación/advertencia.
Reparación no tiene plazo final capturado y no se reconstruye. Eventos cerrados sin instante
no se pueden asignar a un período acotado; documentar esta cobertura en siguiente tablero.

## Tasks

- [x] Crear36 casos nativos: seis controles de eventos existentes y30 contratos del servicio.
  Reutilizar métodos de fixture, sin heredar clases que contengan tests.
- [x] Preparar transporte temporal con baseline137, respaldo, restauración y snapshot sin cambios.
  Bash/PowerShell/Python válidos; verificador real: dos recibos válidos y21 rechazos.
- [x] Confirmar RED exacto en STAGING:30 Missing work KPI service, seis controles verdes, cero errores.
  Intento20261103-165902-021, respaldo `/var/tmp/mc-rov-kpi-service-red-tL6hSb`;
  producto, configuración y pruebas restaurados, servicio activo.
- [x] Implementar `models/work_kpi.py`, importar servicio y núcleo; mantener permisos originales.
  Implementación local, Black99/pylint10,16 pruebas puras conservadas en GREEN.
- [x] Preparar GREEN36 con respaldo/recuperación fresca y restauración de pruebas.
  Paquete: `.tmp/staging-work-kpi-service-green.ps1`; dos recibos válidos y16 rechazos,
  sintaxis Bash/PowerShell y preflight de hashes aprobados. Ejecutado: véase GREEN final.
  v1 falló antes de instalar por lectura local de acentos del manifiesto; reproducido
  con el precheck real. v2 UTF-8 explícito y bytes fijados al SHA instalado; mismo
  producto/pruebas. Regresión: manifiesto exacto aceptado, cuatro alterados rechazados.
  v2:17 verdes/19 errores QA/0 fallos; recuperación verificada. v3 corrige solo el
  entorno del auxiliar `_team` y cuatro assertRaises a ValidationError concreto;
 36 casos conservados y producto idéntico. Registro `kpi-service-fixture-correction.json`.
- [x] GREEN36 y pruebas puras16; revisar cobertura/seguridad antes del tablero.
 36/36 nativos, cero fallos/errores, intento20261103-173705-971; respaldo QC9PNr.
  Recibo revalidado;139 fuentes exactas, datos intactos, pruebas restauradas y STAGING activo.
- [x] Preparar regresión1282 (1246 anteriores y36 KPI) con fuente exacta y restauración.
- [ ] Ejecutar regresión1282 en STAGING y validar el recibo de ese intento.
- [ ] Regresión completa apropiada al cambio y revisión independiente al terminar la entrega.

## Decisiones

Ruling: primera vista por proceso/equipo, sin ranking por empleado — no existe atribución
histórica homogénea — atribuir por cuenta compartida falsearía productividad.

Ruling: solo36 contratos focalizados en el primer RED — las1246 regresiones anteriores
ya pasaron en el baseline; no se modifica producto en este RED — la regresión completa
se repite con servicio implementado, no para cada modificación de pruebas.

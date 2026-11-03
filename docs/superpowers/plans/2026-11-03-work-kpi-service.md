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
- [ ] Confirmar RED exacto en STAGING:30 Missing work KPI service, seis controles verdes, cero errores.
- [ ] Implementar `models/work_kpi.py`, importar servicio y núcleo; mantener permisos originales.
- [ ] GREEN36 y pruebas puras16; revisar cobertura/seguridad antes del tablero.
- [ ] Regresión completa apropiada al cambio y revisión independiente al terminar la entrega.

## Decisiones

Ruling: primera vista por proceso/equipo, sin ranking por empleado — no existe atribución
histórica homogénea — atribuir por cuenta compartida falsearía productividad.

Ruling: solo36 contratos focalizados en el primer RED — las1246 regresiones anteriores
ya pasaron en el baseline; no se modifica producto en este RED — la regresión completa
se repite con servicio implementado, no para cada modificación de pruebas.

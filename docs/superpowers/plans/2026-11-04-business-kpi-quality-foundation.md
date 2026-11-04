# Cálculos de calidad empresarial Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans inline task-by-task. Se conserva el método autorizado por el usuario: implementación aquí y revisión independiente final.

**Goal:** Comprobar las reglas acordadas de retornos, primer pase y liberación mediante cálculos puros, antes de conectarlas con captura y tablero.

**Architecture:** Un módulo Python sin Odoo recibe evidencia ya normalizada y autorizada. Devuelve resultados con cobertura explícita; no consulta ni modifica documentos. El servicio de etapas existente conserva su contrato.

**Tech Stack:** Python estándar, datetime/date y unittest; Black99 y pylint del repositorio.

**Spec:** docs/superpowers/specs/2026-11-04-kpi-catalogo-consolidado.md

## Global Constraints

- Retornos:180 días desde salida del taller; ventana independiente de garantía.
- Corte por fecha civil cerrada. Adaptador futuro convierte instantes a America/Santiago; aquí solo se aceptan Date, sin inventar horas.
- Retorno en fechas salida+0 hasta salida+180 inclusive entra en ventana; +181 no.
- Cohorte madura exige fecha de salida conocida, corte al menos +180 y cobertura desde salida hasta +180.
- Primera aceptación: observaciones informativas permitidas si cumple todo lo obligatorio y no requiere corrección/reensayo.
- Liberación: pruebas aprobadas, documentación completa y ninguna NC bloqueante; salida física es otro evento.
- Ausencia de evidencia no es éxito ni cero fallas; no deducir relación causal por compartir serie/componente.
- No cambios a __init__, modelos/ACL/vistas Odoo, pruebas nativas o versión. No instalar, activar cuentas/políticas ni tocar STAGING/QA/producción.

## Review Focus

1. Una visita con varios retornos cuenta una afectada; cada evento tiene identidad única y duplicados conflictivos se rechazan.
2. Visitas recientes, cobertura incompleta y relación pendiente no mejoran artificialmente la tasa.
3. Día180 incluido, día181 excluido; hechos posteriores al corte no se anticipan.
4. Reabrir/reaprobar o invalidar sin respaldo no borra el primer fallo formal.
5. Documento emitido o checks desconocidos no prueban liberación; una condición bloqueante conocida prevalece sobre desconocidos.

## Archivos y contratos

- Create: models/business_kpi_metrics.py, cálculos puros de estas tres reglas.
- Create: tests/unit/test_business_kpi_metrics.py, escenarios del contrato sin BD.
- Update: docs/pendientes.md, estado local distinto de integración/instalación.
- No ampliar build_metrics ni get_summary de los KPI de etapas.

### Task1: Cohortes de retornos

**Interfaces:** `related_return_metrics(visits, return_events, *, as_of, window_days=180) -> dict`.

`visits` contiene identidades únicas visit_id, delivered_on, coverage_from y coverage_until
(Date o None). Son visitas elegibles filtradas por el adaptador, no órdenes arbitrarias.
`return_events` contiene event_id único, visit_id original, returned_on (Date o None)
y relation en confirmed/pending/unrelated. Dos filas idénticas del mismo evento se
deduplican; la misma identidad con datos contradictorios o un original ajeno al
conjunto recibido produce ValueError. Ninguna relación se infiere en el cálculo.

Salida: window_days, eligible, mature, following, coverage_unknown, affected_mature,
pending_relation_mature, recent_affected, recent_pending, unknown_return_dates,
observed_returns, observed_related_returns, observed_pending_returns,
observed_unrelated_returns, undated_returns_by_relation, value e is_minimum.
value =100*affected_mature/mature o None. Contadores descriptivos conservan eventos
sin fecha y su relación; no los asignan a ventana/período. El adaptador debe entregar
evidencia conocida al corte, sin reconstruir un histórico con registros posteriores.
is_minimum indica relación/timing por resolver dentro de la población madura.
Las categorías mature/following/coverage_unknown particionan visitas; unknown_return_dates
cuenta eventos sin fecha, sin fabricar su pertenencia a ventana. Hechos futuros se ignoran.

- [x] Escribir casos:2 visitas afectadas/10 maduras con3 retornos y4 recientes =20%;
  sin base =None; límites179/180/181; cobertura inicial/final ausente; fecha de salida
  ausente; relación pendiente y evento sin fecha; corte anterior al evento; duplicados.
- [x] Ejecutar unittest: RED por función ausente, cero errores de preparación.
- [x] Implementar firma/contrato; sin reloj global ni mutación de inputs.
- [x] Repetir clase y verificar GREEN; revisión amplía conteos descriptivos y cobertura.

### Task2: Primer veredicto formal

**Interfaces:** `first_pass_status(attempts) -> str`, uno de passed/failed/pending/invalid_only/unknown.

Cada fila pertenece al mismo episodio formal y tiene ordinal positivo único,
validity valid/invalid/unknown, verdict passed/failed/pending, required_passed,
required_failure, correction_required y retest_required. Los últimos campos son
bool o None. El adaptador futuro conserva perfil/episodio y aplica permisos; este
cálculo no es una autorización para cambiar evidencia. Invalidar exige
invalidation_confirmed=True e invalid_reason no vacío para omitir ese intento.

Ordenar por ordinal. Omitir únicamente inválidos respaldados; el primer intento
adjudicable decide. Un required_failure=True siempre conserva failed, incluso si
la fila declara invalidación; no quitar el fallo real del denominador. Flags de
evidencia distintos de bool/None se rechazan con ValueError. Corrección o reensayo requerido =>failed aunque
falte completar el protocolo. Pending no se salta por un aprobado posterior.
Passed requiere required_passed=True y ambos pendientes=False. Evidencia insuficiente
=>unknown; todos inválidos respaldados =>invalid_only; vacío =>unknown.

- [x] Escribir casos de aprobación informativa, fallo seguido de aprobación, pendiente
  anterior, fallo que aborta, invalidación respaldada/no respaldada, datos faltantes y ordinal duplicado.
- [x] Observar RED por función ausente.
- [x] Implementar firma sin cambiar ni reconstruir documentos.
- [x] Repetir clase y verificar GREEN; corregir prueba inicial que esperaba unknown
  para fallo real con invalidación, por contradecir Q1, antes de modificar código.

### Task3: Condición de liberación

**Interfaces:** `release_status(*, tests_passed, documentation_complete, blocking_nc_count) -> str`.

Primeros argumentos bool/None; contador int no negativo/None (bool no es contador).
Devuelve ready si True/True/0; blocked si algún requisito es False o contador>0;
unknown si no hay bloqueo conocido pero falta evidencia. Tipos inválidos =>ValueError.

- [x] Escribir casos de tres requisitos, cada bloqueo, desconocidos y contador inválido.
- [x] Observar RED por función ausente y luego implementar esa firma.
- [x] Verificar GREEN de toda la suite unitaria KPI existente y nueva, sin repetir
  la suite nativa1282 que este incremento no conecta ni cambia.
- [x] Black99 y pylint10; revisión independiente del incremento y correcciones
  con caso de regresión si aparecen hallazgos. Guardar commit en rama aislada.

Validación local: RED inicial31 casos/44 fallos por ausencia; primer pase10 casos
en RED tras nueva regresión; liberación7 en RED. Revisión independiente detectó
tres P2 de contabilización/estado, reproducidos como RED34/9 fallos/0 errores antes
de corregir. GREEN final50/50 unitarias (34 nuevas y16 anteriores), cero errores.
Hooks y guardado se anotan en el ledger al completar el commit.

## Comandos de verificación

PowerShell, desde el checkout aislado, con el Python existente:

```powershell
$env:PYTHONPATH=(Join-Path $PWD 'models')
python -m unittest discover -s tests/unit -p 'test_business_kpi_metrics.py' -v
python -m unittest discover -s tests/unit -p '*kpi_metrics.py' -v
```

En este entorno usar el ejecutable Python fijado del workspace si python no resuelve.
Esperado RED: fallos AssertionError por funciones ausentes; GREEN:0 fallos/errores.

## Incrementos posteriores, fuera de este plan

1. Captura durable: promesa original/cambios, intervalos de bloqueo, primer veredicto,
   relación del retorno y evidencia de liberación. Reutilizar HH, causas, chequeos y PDF.
   Verificar configuración instalada de mc.rov.chequeo/quality.point antes de crear perfiles;
   las semillas noupdate no prueban configuración vigente ni umbrales por modelo.
2. Cálculos de flujo y proveedores + servicio empresarial autorizado separado del
   resumen de etapas. Incluye calendarios Santiago, cantidades/series/visitas y cobertura.
3. Tablero de11 familias y paneles D1/P-NC/P-PRE/P-ET, con navegación nativa y pruebas
   de permisos, roles, empresas, ambos temas y casos ficticios completos.
4. Regresión instalada, carreras, QA operativo, revisión final e integración según
   el método autorizado. Nada de este plan declara entregado el tablero empresarial.

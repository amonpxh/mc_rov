# Centro de trabajo ROV — plan de implementación

> Para ejecución: usar superpowers:executing-plans, con un solo implementador.
> Estado: aprobado el 2026-10-08; piloto y menú activos en STAGING 19.0.24.3.0.
> Suite integrada 378/378, contratos finales 16/16 y HOOT 10/10 aprobados.
> Piloto aprobado por el usuario; suite final del árbol de entrega 378/378 verificada.
> Revisión final realizada y sus tres hallazgos corregidos mediante RED→GREEN.
> PR #100 integrado en main (`b9410ba`); checks del PR y del merge aprobados.
> Producción 19.0.24.3.0 instalada el 2026-10-08; servicio activo, menú/icono y
> accesos de lectura verificados, PDFs conservados. Falta comprobación visual allí.

**Objetivo:** comenzar y retomar trabajo ROV desde la composición C aprobada.

**Arquitectura:** acción cliente OWL con seis necesidades y destinos nativos.
Servicio abstracto de lectura/acciones en mc_rov: no nueva tabla de tareas, estados
ni registros de proceso. Dominios compartidos entre conteos, filas y listas; abrir
un registro no crea otro. Mantener navegación y formularios actuales.

**Tecnologías:** Odoo 19 Enterprise, ORM, OWL, SCSS, pruebas transaccionales y HOOT.

**Diseño:** [Centro de trabajo ROV](../../designs/centro-trabajo-rov.md).

## Restricciones globales

- Seis nombres aprobados; conservar «Aceptar un equipo nuevo» y «Trabajar en diseño / BoM».
- Descripción: «Modelos, BoM (lista de materiales) y cambios de ingeniería».
- No copiar HTML del prototipo al bundle productivo; reimplementar con OWL.
- Consultar equipo: modelo opcional + serie + estado operativo.
- Catálogos y equipos no son tareas pendientes; nunca sumar conteos entre tipos.
- No nuevos requisitos, asignaciones personales, cambios de reportes ni despliegue PROD.
- Registros sujetos a ACL, reglas, compañía y ámbito ROV; no sudo sobre registros de trabajo.
- Reutilizar stock.lot._get_rov_root_category; su lectura de configuración elevada
  no autoriza elevar consultas de órdenes, unidades, Calidad o ingeniería.
- Si la categoría ROV no resuelve, informar configuración no disponible; no abrir
  silenciosamente todos los productos ni presentar cero como resultado válido.
- No crear, emitir, aplicar ECO o modificar BoM al seleccionar una tarjeta.
- Conteos y filas obtenidos del servidor, nunca números demostrativos en Odoo.

## Riesgos que deben cubrirse

1. Usuario con acceso parcial: tipos restringidos no revelan conteos ni nombres.
2. Registro borrado o acceso revocado: no abrir otro por sustitución ni quedar cargando.
3. Búsquedas simultáneas: una respuesta antigua no reemplaza el área elegida después.
4. Filtros al volver: conservar tipo, modelo, búsqueda y estado; refrescar resultados.
5. Categoría/compañía: no mezclar componentes no-ROV ni registros fuera del acceso actual.

## 1. Verificar contratos de la instalación

Archivos de evidencia local: `.tmp/center-work-audit/probe.sh`,
`.tmp/staging-center-work-audit.ps1`, `.tmp/center-work-audit/installed.json`.

- [x] Preparar sonda de solo lectura y comprobar sintaxis PowerShell.
- [x] Ejecutar en terminal del usuario con contraseña SSH; confirmar rollback.
- [x] Contrastar selecciones de estado y campos relacionales por modelo, acciones
  nativas, grupos de menú y fuentes del servicio de acciones de Odoo instalado.
- [x] Registrar XML IDs escogidos y contexto nativo en el diseño antes de escribir
  acciones productivas. La consulta de acciones no implica acceso de todo usuario.

La sonda incluye repair.order, revisión, fabricación, equipo, FEN, alerta/control,
producto, BoM y ECO. No instala ni reinicia; no emite ni crea datos QA.

Destinos verificados en `installed.json`:

| Tipo | Acción a reutilizar |
| --- | --- |
| Órdenes de reparación | repair.action_repair_order_tree |
| Revisiones/RND/TRN | mc_rov.action_mc_rov_prueba_realizada, con tipo y ámbito explícitos |
| Fabricaciones | mrp.mrp_production_action |
| Equipos | stock.action_production_lot_form |
| FEN | Acción list/form del modelo existente; no hay acción general instalada |
| Alertas y lecciones | quality_control.quality_alert_action_check, con filtros distintos |
| Controles | quality_control.quality_check_action_main |
| Modelos | mrp.product_template_action |
| BoM | mrp.mrp_bom_form_action |
| Cambios de ingeniería | mrp_plm.mrp_eco_action_main |
| Candidatas a lección | mc_rov.action_mc_rov_leccion_pendiente |

No reutilizar acciones específicas de origen con `active_id` desde el centro.
Las listas adoptarán modo list primero para coincidir con la maqueta. Conservar
dominios nativos pertinentes (compañía/ubicación de lotes, picking activo de MO),
combinados con ámbito ROV. Quitar defaults de búsqueda que contradigan Todos los
estados, por ejemplo search_default_todo de fabricación. Evaluar contexto con
compañías reales; nunca transportar expresiones de `active_id` no definido.

Estados confirmados: revisión `borrador/confirmado`, FEN `borrador/emitida`,
control `none/pass/fail`; alertas cerradas por `stage_id.done`. ECO usa `state`
(`confirmed/progress/rebase/conflict/done`), no asumir `stage_id.done` porque ese
campo no está presente en mrp.eco.stage. Equipos no tienen `active`: no añadir
dominios de archivado sobre stock.lot. Respetar baja explícita mc_fecha_baja.

## 2. Servicio de lectura y acciones con prueba RED/GREEN

Crear `models/mc_rov_work_center.py` y `tests/test_work_center.py`.
Modificar `models/__init__.py` y `tests/__init__.py` para incluir ambos completos
en payloads: no repetir imports de archivos ausentes en STAGING.

Interfaz propuesta de `mc.rov.work.center` (AbstractModel):

```python
get_overview()  # áreas/tipos disponibles, capacidades y conteos por tipo
get_records(topic, kind, state_filter="open", query="", model_id=False, offset=0)
# {rows: [{id, reference, context, state}], total, next_offset}
action_open(topic, kind, record_id)  # acción nativa, formulario exacto
action_list(topic, kind, state_filter="all", query="", model_id=False)
action_create(topic, kind)  # formulario nativo; crear solo al guardar
```

Tipos y filtros son claves de allowlist del servidor; rechazar modelos/campos,
estados y destinos arbitrarios enviados por RPC. Filas paginadas de 20, consulta
limitada a 100 caracteres, orden estable por fecha/id o nombre/id para catálogos.
No cargar todo el catálogo para filtrar en navegador.

- [x] Escribir contratos antes del servicio: ROV/no-ROV, tipos correctos,
  borrador/emitida, búsqueda/modelo y conteos/listas con mismo ámbito.
- [x] Escribir contrato de apertura: dos FEN del mismo equipo; abrir la ID elegida
  conserva su RND/TRN y no cambia número de fichas. Assert central:

```python
action = center.action_open("acceptance", "fen", chosen.id)
self.assertEqual(action["res_id"], chosen.id)
self.assertEqual(action["res_model"], "mc.rov.ficha.equipo.nuevo")
self.assertEqual(chosen.rnd_id, original_rnd)
self.assertEqual(chosen.trn_id, original_trn)
```

- [x] Prueba de permiso: ocultar una unidad por regla de registro; su ID no aparece
  en filas/conteos y action_open sobre ella produce AccessError, no fallback.
  Probar falta de ACL a un tipo sin impedir consultar otro permitido.
- [x] Ejecutar RED en STAGING; comprobar fallo por servicio ausente, no import/API.
- [x] Implementar `_get_definition(topic, kind)` y `_get_domain(...)` como únicas
  fuentes de ámbito. Reutilizarlas para search_count, search y action_list.
- [x] Implementar lectura y acciones; acceso interno explícito, sin mutaciones.
  Verificar permiso de creación antes de anunciarlo o abrir formulario nuevo.
- [x] Ejecutar GREEN focalizado con `/mc_rov:TestWorkCenter`; guardar salida.

Ámbitos: reparación/fabricación/producto/BoM/ECO por categoría ROV; equipo por
es_un_rov; FEN por equipo; revisión por equipo y tipo real. RND/TRN de aceptación
no deben incorporar revisiones vinculadas a reparación. Calidad usa relaciones
reales a productos/unidades ROV: verificar sus dominios en la sonda y mantener
lecciones cerradas con prevención diferenciadas de candidatas a lección.

Las listas de equipos para aceptación son selección de unidad, no cola inferida
de «equipos que necesitan aceptación». Crear rendimiento/terreno/FEN comienza
abriendo equipo para elegir explícitamente la unidad y usar sus acciones existentes.

## 3. Acción cliente y estado de navegación

Crear `static/src/work_center/work_center.js`, `work_center.xml`,
`work_center.scss`, `static/tests/work_center.test.js`.
Modificar `__manifest__.py` para backend, pruebas HOOT y vista del centro.

- [x] Escribir pruebas frontend de selección de área/tipo sin creación; apertura
  recibe la ID de la fila; acceso no permitido no muestra botón; filtro modelo
  sobrevive a ida/vuelta; respuesta antigua no cambia la selección actual.
- [x] Observar RED frontend antes de componente; no confundir bundle instalado
  con tests ejecutados. Ejecución HOOT en navegador con resultado visible.
- [x] Implementar client action `mc_rov.work_center` mediante registry actions;
  consumir ORM y action service, sin patch global de FormController/chatter.
- [x] Estado por área y tipo: búsqueda, modelo, estado, página y selección.
  Integrar restauración en action stack según fuentes instaladas verificadas.
- [x] Debounce de búsqueda 250 ms y generación de petición: aplicar respuesta
  solo si sigue siendo la solicitud vigente. Mostrar carga/error sin filas antiguas
  atribuidas al nuevo tipo. Reintentar lectura explícitamente.
- [x] Diseño responsive aprobado: seis tarjetas, selección lateral, pestañas,
  conteos, filtros locales y creación a la derecha. Etiquetas accesibles y foco visible.
- [x] Sin acceso es diferente de cero; errores de red distintos de lista vacía.
  Estado vacío ofrece lista completa o acción autorizada, sin inventar registros.
- [x] Observar GREEN HOOT y comprobar navegación de regreso con formulario nativo.

No publicar selector de variantes A/B/C ni banner de datos ficticios en Odoo.
Etiquetas reales del estado vienen del modelo; no duplicar sus selecciones.

## 4. Entrada ROV y piloto STAGING

Crear `views/mc_rov_work_center_views.xml`: ir.actions.client y entrada **ROV →
Centro de trabajo**. No sustituir home Odoo ni quitar menús nativos existentes.
Versionar módulo compatible al instalar; comprobar rama feature antes de código.
El trabajo documental actual sigue en `docs/centro-trabajo-rov`; crear rama feature
con esas decisiones conservadas al comenzar implementación.

- [x] Probar menú visible para usuario interno y permisos por acción/type;
  no agregar ACL sobre modelos de negocio para que el dashboard «funcione».
- [x] Preparar helper STAGING con respaldo, lock, rollback de QA, restauración de
  código/vistas ante fallo y reinicio final; normalizar LF y transportar archivos completos.
- [x] Pasar focalizados, HOOT y suite mc_rov una vez con código integrado.
- [x] Verificar hashes QWeb FEN/REV conservados; no generar PDFs por un cambio de navegación.
- [ ] QA manual: abrir órdenes/revisiones; modelo y serie; FEN elegida;
  modelos/BoM/cambios; alertas/controles/lecciones según muestras disponibles.
  Marcar casos sin muestra como pruebas transaccionales, no clic real certificado.
- [x] Verificar filtros al volver y pantalla estrecha. No tocar datos de clientes
  para producir escenarios de prueba. Mantener producción sin cambios.
- [ ] Actualizar pendientes con evidencia, review del diff y PR después de aprobar
  el piloto; integración/deploy se resolverán como entrega separada.

## Revisión propia del plan

Contenidos C, filtros, nombres, permisos, scopes, estado de navegación, errores y
límites cubiertos por tareas 1–4. Riesgos 1/2/5 tienen pruebas backend; 3/4 frontend
y retorno nativo. No nueva persistencia ni tareas personales. La sonda instalada
es la dependencia previa a escribir dominios y acciones productivas; una maqueta
correcta no certifica contratos internos de Odoo.

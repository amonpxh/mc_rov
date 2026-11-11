# Tablero de gestión ROV y continuación de las once fichas

Fecha: 2026-11-11. Estado: aprobado por el usuario con «ok go» el 2026-11-11.
No modifica código de producto ni autoriza instalar, integrar o activar políticas.

## Base confirmada

Producción instalada: 19.0.25.7.0, commit36e0f37, aceptación final y servicios KPI.
Servicios disponibles:

- `mc.rov.repair.acceptance.kpi.get_summary(repair_ids)`.
- `mc.rov.new.acceptance.kpi.get_summary(production_ids)`.
- `mc.rov.work.kpi.get_summary(date_from, date_to, process)`.
- Centro nativo: consulta de cartera y acciones con alcance ROV/empresa/permisos.

Las dos primeras consultas clasifican una selección actual explícita. No admiten
período ni demuestran una cohorte mensual. La tercera mide etapas, no unidades.
Una tarjeta visual no cambia esos contratos por suposición.

Fuente de negocio vinculante: `docs/superpowers/specs/2026-11-04-kpi-catalogo-consolidado.md`
del repositorio. Mantener 22 familias, once en el resumen inicial (F1–F6,Q1–Q4,A1),
con D1 y señales operativas. No sumar listas históricas ni inventar nuevos indicadores.

## Objetivo

Que quien coordina el taller pueda consultar cartera actual, primera aceptación,
pendientes de seguimiento y cobertura, abrir documentos autorizados y distinguir
qué se puede medir de qué aún requiere captura. Continuar el resto de fichas por
recorridos completos y revisables, sin reemplazar evidencia ausente por cero.

## Pantalla propuesta

Decisión de implementación de Codex: nueva entrada **Indicadores** dentro de
**Centro de trabajo**, junto a la entrada existente. Vista OWL de Odoo, con sus
servicios y estilos existentes; sin sitio externo, dependencias nuevas ni rol nuevo.
No agregar otra pestaña a cada revisión ni mezclar tarjetas KPI con tareas pendientes.

Esquema de navegación:

```
Centro de trabajo > Indicadores
[Resumen] [Calidad] [Seguimiento] [Cobertura y definiciones]    [Actualizar]

Resumen: Cartera actual (órdenes, no equipos) | Primera aceptación (n/N)
Calidad: Reparaciones | Equipos nuevos; aprobado/fallido/pendiente/sin evidencia
Seguimiento: pendientes/vencidas/cierres reales por proceso; original y vigente
Cobertura: once fichas, fuente, unidad, población y dato que falta
```

### Resumen y Calidad

- Cartera actual de órdenes ROV de reparación y fabricación, separadas; emplear
  exactamente el alcance de Centro, sin contar MO como unidades fabricadas.
- Primera aceptación de reparaciones y equipos nuevos en tarjetas distintas:
  porcentaje, aprobados/evaluados, fallidos, pendientes y sin evidencia; cobertura
  evaluados/población. Mostrar «Sin base» cuando evaluados=0, nunca 0% por defecto.
- Rótulo de cohorte: **Selección actual de órdenes ROV, al actualizar**. Detalle de
  selección visible; no usar fecha de creación de una orden como fecha del primer pase.
- Decisión de implementación de Codex para la selección inicial: todas las órdenes
  ROV accesibles de las empresas activas, incluidas cerradas y archivadas, sin el
  filtro «abiertas» de cartera ni el límite de veinte filas de su lista. Reparación
  conserva como desconocida una orden sin evidencia formal; no convierte una orden
  cancelada o en borrador en intento evaluado. El rótulo de cobertura es «de la
  selección consultada», no cobertura de una cohorte histórica elegible. Equipos
  nuevos cuenta solo unidades realmente fabricadas que devuelve su adaptador,
  aunque la selección de MO incluya órdenes sin producción efectiva.
- Para agregar, consultar la población completa autorizada. La paginación solo
  afecta la lista de detalle. No sumar porcentajes ni contar dos veces una unidad
  por grupos/parciales de MO. Al abrir el detalle, quitar el filtro nativo de
  «abiertas» cuando contradiga esta selección y conservar el dominio autorizado.
- El usuario ve la definición de esa selección. No se ofrece selección manual de
  casos para mejorar una tasa en este incremento. Si no puede leer una revisión
  histórica necesaria, Q1 queda «Sin acceso al historial requerido», conservando
  el límite del servicio; no quitar silenciosamente ese fracaso del denominador.
- No hay filtro global de período para estas tarjetas en este incremento: los
  adaptadores actuales no lo implementan. El corte temporal histórico empresarial
  se incorpora después de verificar hitos y cohortes; no se simula en JavaScript.
- Abrir listas/documentos con acciones nativas; al volver, conservar sección y
  selección. Los detalles no hacen pública la tabla privada de intentos.

### Seguimiento

- Seis procesos existentes: Reparación, Fabricación, Aceptación, Calidad,
  Ingeniería e Inventario. Es seguimiento de etapas, no producción del taller.
- Pendientes y vencidas son actuales; fecha de corte visible. Los filtros de fechas
  se aplican exclusivamente a cierres, con advertencia persistente junto al selector.
- Cierres reales, cancelaciones y cierres manuales históricos se muestran separados.
- Plazo original y vigente capturado separados, con n/N y desconocidos. Duración
  mediana rotulada «horas corridas de etapa», nunca HH ni plazo total del cliente.
- El servicio actual usa la zona capturada por seguimiento; mostrar esa regla.
  Los próximos KPI empresariales usan America/Santiago, semanas lunes–domingo
  y meses/años calendario como se acordó; no reinterpretar silenciosamente datos
  del servicio actual como otra zona.

### Cobertura y definiciones

Cada ficha muestra estado funcional, qué decisión sirve, unidad, fuente, población,
fórmula y qué dato falta. Estados distintos: disponible, sin evidencia, captura
pendiente, sin base y sin acceso. No anunciar como disponible una cifra aún no calculada.
No exponer conteos restringidos ni nombres de documentos inaccesibles en mensajes.

## Once fichas: siguiente trabajo concreto

| Ficha | Base actual comprobada | Entrega pendiente antes de su cifra empresarial |
|---|---|---|
| F1 Cartera | Estados y alcance ROV actuales de Centro | Separar cartera técnica/salida física; eventos de entradas, reaperturas y saldos históricos antes de mostrar su balance |
| F2 Detenciones | Causas acordadas; disponibilidad nativa solo señal | Capturar inicio/fin, causa, responsable de destrabar e intervalos solapados; una falta no es detención si se puede avanzar |
| F3 Compromisos | Transferencias y venta como candidatos | Promesa original firme, recompromisos con motivo/autor y constancia/fecha efectiva de salida; abiertas vencidas incluidas |
| F4 Reparaciones terminadas | Orden/serie; candidato movimiento de cierre | Auditar primer cierre válido y conservar reapertura/recierre; visitas y series distintas, fecha de creación no sustituye cierre |
| F5 Fabricaciones por hito | Identidad por unidad/grupo y aceptación sellada | Conciliar salida fabricada, cantidades/series/parciales; aceptación, liberación y despacho como hitos distintos |
| F6 Plazo de reparación | HH y algunos eventos | Verificar recepción física, diagnóstico, autorización, cierre y salida; no reconstruirlos desde write_date |
| Q1 Primera aceptación | Ambos adaptadores instalados | Presentación y selección explícita ahora; adaptación temporal solo con cohorte de eventos comprobada |
| Q2 Retornos relacionados | Núcleo de cálculo puro y ventana180d acordada | Enlace visita original/retorno, dictamen y seguimiento observado antes de calcular tasa madura; no inferir ausencia de falla |
| Q3 Retrabajo | HH y causas como candidatos | Clasificar retrabajo real frente a alcance adicional, enlazar evento/HH y evitar multiplicación por joins |
| Q4 Hallazgos/Pareto | Catálogos y observaciones en revisiones | Auditar vínculo, fecha y categorías; Pareto de observaciones primero, no llamarlo incidentes únicos sin identidad |
| A1 Proveedores | Compras/recepciones nativas disponibles | Auditar compromiso original por línea, parciales y recepción completa; fecha actual reprogramada no reemplaza promesa original |

Metadatos ya auditados localmente (sin nueva consulta al servidor):
`repair.order.fecha_entrega_real` es Date editable, no cierre físico sellado;
`mrp.production.date_finished` y movimientos/series existen; `purchase.order.line.date_planned`
es editable. Su presencia no acredita las identidades o promesas originales que
exigen las fichas. Reutilizar auditorías existentes antes de solicitar otra.

No se retiran las fichas pendientes: quedan visibles como trabajo de captura y
medición, con sus definiciones, sin números ficticios ni fórmulas inventadas.

## Orden de implementación propuesto

1. Pantalla, lectura agregada autorizada, cartera actual, Q1 y seguimiento/D1 con
   los servicios existentes. Entrega pequeña que puede comprobarse completa.
2. Auditar solo los vínculos/fechas que faltan para F4/F5/Q4; entregar producción
   por período y cliente cuando su atribución esté respaldada, y Pareto por unidad
   explícita. No continuar ampliando contadores de actividades para imitarlos.
3. Captura y cálculo de compromisos/salida/detenciones/tramos (F2/F3/F6 y extensión
   histórica de F1). La prioridad comercial se mantiene; no se calcula sin base.
4. Retornos180d, retrabajo y proveedor original (Q2/Q3/A1). Reutilizar Compras nativo;
   si falta una decisión comercial o evidencia, resolverla antes del porcentaje.

P-NC y P-PRE se incorporan con fuentes de severidad y liberación comprobadas;
no inferir preparación por ausencia de una alerta o por una ficha emitida.

## Autorización y seguridad

Consulta interna del equipo y permiso de lectura de cada origen, empresas activas
validadas por Odoo. Sin acceso no es cero. Cliente histórico, empleados y costos
no se filtran ni muestran si el dato/permiso no existe. Sin ranking por cuenta.
No nuevas ACL en historiales privados, ni sudo para ampliar fuentes seleccionables.
No se cierra, crea o edita trabajo desde el tablero. «Actualizar» solo consulta.
No devuelve snapshots privados ni deriva permisos de valores del navegador.

## Contratos de verificación

- Numerador/denominador cero, pending/unknown, sin acceso y empresa ajena.
- Una orden reabierta no se transforma en otra visita por cambiar la vista.
- Una MO con dos unidades y parciales no se cuenta como un solo equipo ni tres MO.
- Fallo inicial seguido de aprobación conserva fallo de primera aceptación.
- Filtros de cierre no modifican pendientes actuales; no aplicarlos a Q1 sin cohorte.
- Conteos de cartera y acciones de detalle tienen el mismo dominio autorizado.
- Error de RPC, cambio de empresa, respuesta tardía y navegación ida/vuelta.
- No filtrar por estado actual un fracaso histórico para mejorar el porcentaje.
- Lectura no cambia datos, permisos, stock, actividades, calendarios o PDFs.
- HOOT de interfaz y pruebas Odoo focalizadas; suite integral solo cuando haya
  cambios de producto que justifiquen la regresión. QA ficticio aislado y cerrado al terminar.

## Fuera de este incremento

Metas numéricas y semáforos rojo/verde no acordados; ranking de personas; rentabilidad
sin conciliación; KPIs de flota inferidos de retornos al taller; agentes IA y cambios
en Compras. No publicar, integrar ni desplegar por aprobar el diseño de la pantalla.

## Decisiones de implementación que quedan a revisión

Entrada propia Indicadores en Centro, cuatro secciones y cohortes actuales claramente
rotuladas en el primer incremento. El calendario empresarial y once fichas no cambian.
La continuidad del resto se hace por hitos comprobados, no con una tarjeta vacía
presentada como KPI implementado. No reabrir las copias QA cerradas por rutina.

Revisión de construcción independiente: `/root/kpi_dashboard_builder_check` detectó
una ambigüedad material en la población Q1 inicial. Resuelta arriba por las reglas
ya acordadas: incluir historial cerrado y no usar páginas de veinte como población.
Esta selección inicial es una decisión de implementación propuesta, visible al
usuario; no constituye un nuevo criterio comercial de elegibilidad ni una meta.

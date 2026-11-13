# Reparaciones terminadas, unidades fabricadas y Pareto

Estado: propuesta para revisión; no implica implementación, instalación ni activación.
Continúa las fichas F4, F5 y Q4 del catálogo consolidado del 4 de noviembre.

## Decisiones del usuario

- «Revisión» significa diseño/configuración del modelo ROV, no revisión técnica.
- Comparar todas las revisiones o una concreta; vista inicial de la última revisión.
- La empresa no fabrica prototipos: no crear una finalidad por fabricación ni un
  catálogo de prototipos para resolver una distinción que no utiliza.
- Para liberar un equipo nuevo, el único documento exigido es la Ficha de Equipo
  Nuevo. Supervisor valida la liberación. Se mantienen rendimiento y terreno
  aprobados y ninguna no conformidad bloqueante pendiente.
- Mantener las definiciones, fechas y coberturas del catálogo acordado. Hora de
  Santiago, semanas lunes–domingo, meses y años calendario.

## Objetivo y presentación

Agregar Producción y Hallazgos al tablero existente. Producción muestra reparaciones
terminadas y unidades por hito; Hallazgos muestra frecuencias y Pareto. Mantener las
secciones existentes y navegación hacia fuentes autorizadas. No sumar visitas y
unidades como si fueran la misma magnitud.

Filtros compartidos: período, empresa activa, modelo y revisión de diseño.
Cliente, intervención, componente y severidad aparecen donde tienen significado.
La pantalla identifica fecha, población y unidad de cada cifra. Presentar cantidad,
cobertura y desconocidos juntos; sin evidencia no significa cero ni fallo.

## Fuentes comprobadas y límites

Auditoría de metadatos y métodos en odoo_test, CI 43233553711, HEAD 9d207a3:
11 modelos, transacción READ ONLY y rollback. Sin registros individuales ni acciones
de negocio. El mismo CI conserva las 1558 pruebas Odoo anteriores en verde.

- repair.order.action_repair_done crea el movimiento del producto reparado, lo
  completa y después establece state=done. No prueba despacho físico al cliente.
- mrp.production.button_mark_done procesa parciales, publica inventario y finalmente
  marca la fabricación realizada. La cantidad planificada no acredita producción.
- mrp.eco.action_new_revision crea BoM de prueba inactiva con previous_bom_id;
  action_apply aplica la nueva BoM o actualiza product.template.version. Una revisión
  en preparación no es automáticamente la vigente.
- Hallazgos tienen create_date y catálogos, pero no detected_at/fecha propios ni
  identidad de incidente. Su fecha de creación no acredita detección física.
- Las versiones actuales de producto y BoM son campos almacenados editables.
  Leerlos hoy no basta para reconstruir la configuración histórica de una serie.

Antes del plan de captura, completar la lectura técnica de apply_new_version,
resolución de BoM y cambios de bom_id en fabricación. No modificar PLM para medirlo.

## Revisiones de diseño

Propuesta técnica: reutilizar identidad nativa de producto/configuración, BoM y ECO,
sin crear otro catálogo editable de versiones. Conservar referencias y etiquetas
selladas en los eventos para que renombrar un catálogo no reescriba el pasado.

«Última» significa vigente y aplicada por modelo/configuración, nunca el máximo
global ni un ECO borrador. Si hay varias configuraciones válidas, resolver cada
una por separado; si hay ambigüedad, mostrarla en cobertura sin elegir arbitrariamente.
Mostrar qué revisiones incluye el filtro inicial y permitir pasar a Todas.

La fabricación conserva su configuración efectivamente utilizada; no se actualiza
al aplicar después otro ECO. Para una reparación, distinguir configuración conocida
del equipo de una revisión de diseño vigente del catálogo: no asignar una a la otra
sin evidencia. Un equipo modernizado requiere evidencia de ese cambio para afirmar
una revisión distinta. Hasta entonces corresponde «Sin revisión acreditada».
Los desconocidos permanecen visibles incluso con el filtro Última, separados del
numerador conocido; no presentarlos como pertenecientes a esa última revisión.

## F4: primer cierre técnico por visita

Contar una orden/visita una sola vez, por su primer cierre técnico válido en período.
Mostrar además series distintas. Tres visitas sobre dos series producen 3 visitas y
2 equipos; reapertura y recierre no producen una cuarta visita.

Captura propuesta: evidencia privada y transaccional del primer cierre válido,
independiente de las políticas de actividades y sin activarlas. Guardar origen,
empresa, equipo/producto, cliente de la visita, intervención, garantía, fecha/actor
y revisión de diseño acreditada. Comprobar movimiento done del equipo cuando el
cierre use el recorrido nativo; un write directo o importación a done no debe
fabricar evidencia equivalente. No modificar las reservas ni el cierre nativo.

La fecha declarada fecha_entrega_real conserva su función existente y no se usa
como sello inmutable. Las órdenes antiguas sin evidencia quedan en cobertura;
ningún backfill automático. Una corrección conserva el evento original, motivo y
autor; no borrar historia ni permitir edición genérica para cambiar el indicador.
No permitir correcciones desde el tablero en este incremento.

## F5: unidades por hito

Identidad: empresa, episodio de fabricación y serie final ROV. Conservar identidad
entre MO y backorders; no contar componentes, subproductos ni dos veces una serie.
Exponer incoherencias y cantidades sin serie, sin descartarlas silenciosamente.

- Fabricada: salida de producto final done con cantidad positiva y serie válida.
- Aceptada: aprobación conjunta formal de rendimiento y terreno ya capturada.
- Liberada: rendimiento y terreno aprobados, Ficha de Equipo Nuevo emitida y
  ninguna no conformidad bloqueante pendiente; validación explícita de Supervisor.
  No deducir liberación automáticamente de una FEN emitida. Conservar fecha, actor
  y referencias a la evidencia que Supervisor validó. No exigir otros documentos.
  El rol funcional Supervisor debe mapearse a permisos existentes comprobados;
  esta decisión no concede permisos ni activa cuentas reales.
- Salida al cliente: transferencia efectiva done hacia cliente; una reparación
  posterior del mismo ROV no vuelve a ser una unidad nueva fabricada.

Cada hito tiene fecha y evidencia propias. Mostrar fabricadas/aceptadas/liberadas/
salidas, con pendientes y desconocidos por hito. Un hito sin captura suficiente se
rotula «Captura pendiente», no cero. No entregar F5 como completo mientras falte
liberación o vinculación de salida. Las existencias entre hitos requieren estado
al corte y reversos; no restar acumulados de períodos distintos.

Desmontajes, devoluciones y anulaciones posteriores se muestran aparte. Conservan
la fabricación histórica y modifican el saldo vigente cuando corresponde.
Una MO de dos ROV con parcial 1+1 produce dos unidades; aceptar una, liberar una y
entregar ninguna conserva 2/1/1/0.

## Q4: hallazgos y Pareto

Unidad inicial: observaciones confirmadas. Opciones adicionales: visitas afectadas
y series distintas por categoría; explicar que una misma visita puede tener varias
categorías y que esas columnas no se suman para obtener visitas únicas globales.
No ofrecer «incidentes únicos» hasta disponer de identidad física y continuidad.

Agrupar por hallazgo o componente; mostrar frecuencia, participación y acumulado,
orden descendente con desempate estable. Denominador explícito, incluyendo el
grupo Sin clasificar cuando corresponda; una lista truncada conserva Otros y su
total. Sin metas ni colores de éxito por registrar menos hallazgos.

Separar severidad, síntoma, causa y acción. No convertir severidad en dinero ni
mostrar Pareto de horas/costos sin atribución fiable. Sin causa confirmada queda
Sin determinar; no inferirla del nombre del hallazgo.

Captura propuesta: fecha de detección explícita, contexto de origen y observación
sellada al confirmar. Conservar identificador de observación y correcciones para
que reabrir y reconfirmar no cree otra ocurrencia. No atribuir cliente histórico
usando propietario actual. Observaciones antiguas sin fecha/contexto acreditados
pueden mostrarse como cobertura o registro actual claramente separado, nunca
insertarse en la serie histórica con create_date como detección.

## Permisos e integridad

Reutilizar el permiso de consulta de equipo del tablero y las reglas de cada fuente.
Comprobar fuente, empresa, producto y serie antes de leer evidencia privada. No
filtrar solo la lista visible dejando que el agregado revele otros registros.
Sin permiso no presentar un cero aparente ni exponer IDs del historial privado.

Captura interna mediante capacidad no falsificable por contexto RPC, sin ACL
general nueva para eventos. Evidencia y negocio en la misma transacción: rollback
revierte ambos. Unicidad, bloqueo ordenado y reintentos conservan un evento real
ante dos conexiones; no ejecutar ni repetir movimientos para reparar un KPI.

## Entrega incremental y verificación

1. Fuentes y revisión de diseño: terminar contratos de resolución histórica/vigente.
2. F4: primer cierre, cobertura y tarjeta, con controles de reapertura y acceso.
3. F5: producción por serie/episodio y hitos acreditados, con reversos y parciales.
4. Q4: captura de detección, observaciones y Pareto, con correcciones sin duplicados.
5. Integración visual, filtros, concurrencia y suite completa del producto final.

El orden es una decisión técnica propuesta para entregar incrementos revisables.
No declarar terminadas las tres familias al completar solo el primero.
Usar RED/GREEN focalizado y regresión proporcional por CI; luego pruebas pobladas
de escritorio/móvil y dos conexiones para capturas. Conservar los contratos previos.
Las cuentas ficticias de pruebas no conceden roles a personas reales.

No incluye despliegue, migración de historia antigua, activación operativa, cambios
de stock, nuevas metas, rankings de personas ni integración con IA/Telegram.
Merge, despliegue y activación conservan sus autorizaciones separadas.

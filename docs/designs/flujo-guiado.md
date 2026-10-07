# Recorridos guiados de reparación y fabricación / aceptación

**Decisión 2026-10-06:** el panel de guía junto al chatter (secciones de integración
más abajo) se descarta tras QA real: repetía las pestañas sin explicar qué tarea
seguir. Se retira su código y pruebas específicas. La auditoría de recorridos y
aplicabilidad se conserva. El sustituto aprobado es un aviso contextual de carencias concretas, inspirado
en el aviso de datos técnicos faltantes del equipo y ya validado en STAGING.
Las propuestas de panel inferiores quedan como antecedente histórico.

### Diseño aprobado: aviso de cierre (2026-10-06)

El usuario aprobó mostrar tres carencias verificables: tipo de intervención vacío,
trabajos sin origen y consumo de repuestos sin movimientos en la orden. Coinciden
con `_validar_tipo_intervencion`, `_validar_origen` y `_validar_repuestos` actuales;
no se añade un requisito nuevo. Revisiones borrador no bloquean cierre.

Maqueta descartable en `.tmp/repair-contextual-preview/index.html`, disponible en
`http://localhost:8079/`: refinamiento aprobado, franja ámbar sobre las pestañas con
una frase «Antes de cerrar: …», solo los motivos aplicables, sin enlaces ni botones.
Nombra Tipo de intervención, Origen en Cierre y Repuestos. No hay título separado
ni tres filas. Desaparece sin carencias o en done/cancel;
diagnóstico sin trabajos no exige trabajos ni repuestos. Conteos corresponden a
trabajos sin origen, no a porcentaje de avance ni pasos pendientes universales.

Escenarios visuales: tres requisitos, solo origen, solo repuestos, diagnóstico
completo y orden cerrada. Ausencia de franja en orden cerrada comprobada en navegador;
versión compacta verificada sin enlaces/botones. Captura
`.tmp/repair-contextual-preview/preview.png`. Implementado y validado en STAGING: 349 pruebas sin fallos ni errores y QA visual;
el ajuste de separación pasó seis pruebas adicionales. El aviso comprueba datos faltantes, nunca si una persona «revisó» un registro
ni si abrió una pestaña. No se añade una casilla Revisado.
El código conserva permisos, guardado y navegación nativos; datos no
accesibles no equivalen a cero. Este aviso no resuelve todavía conexiones entre
procesos ni el centro de trabajo. No debe anunciar «listo para entregar».

Revisión: 2026-10-05. Base auditada: main c1d359f; versión funcional 19.0.23.7.0.
Estado: diseño en revisión. Código inspeccionado y primer recorrido de pantalla
realizado en STAGING; práctica de taller y casos restantes por contrastar.
No hay implementación de navegación nueva.

## Auditoría de conexiones en pantalla — 2026-10-06

Base: main `ba6580b`, código funcional `d6e6e5c`, mc_rov 19.0.23.8.0.
Inspección de producción en lectura, sin crear pruebas, fichas ni modificar órdenes.
El túnel STAGING perdió conexión al abrir una revisión; se comprobó el recorrido
con la sesión de producción ya abierta del usuario, sin ejecutar acciones de negocio.

| Tramo | Evidencia de pantalla | Decisión |
| --- | --- | --- |
| MO → equipo | WH/MO/00010 tiene botón nativo «1 Números de serie»; abre lista con 0000008 y permite abrir su ficha | Conservar. No agregar otro botón de equipos producidos. |
| Equipo → prueba existente | 26-02 → Pruebas → Editar en RND/00004 abre el formulario completo | Conservar. No agregar Continuar prueba duplicado. |
| RND → equipo de origen | Al entrar desde 26-02, la ruta superior incluye el equipo y permite regresar | Conservar retorno nativo por esa ruta. |
| Orden → revisión | WH/RO/00019 → Revisiones → Editar en REV/00023 abre su formulario | Conservar. No agregar Continuar revisión duplicado. |
| REV → orden de origen | La ruta superior conserva WH/RO/00019 al entrar desde esa orden | Conservar retorno nativo cuando existe ese contexto. |
| Menú general → REV | Revisiones técnicas → REV/00023 deja solo Revisiones técnicas en la ruta; no la orden/equipo | Corte de orientación: estudiar accesos explícitos a los registros vinculados. |
| Campos vinculados de REV | Número de serie y Orden tienen la flecha nativa Enlace interno; en reposo está oculta por CSS | La relación existe; el problema es descubrimiento y continuidad, no falta de datos. |
| Equipo → FEN existente | La lista está en Pruebas; ambos equipos inspeccionados carecen de FEN registradas | No afirmar que se validó abrir/retomar FEN. Comprobar con un borrador QA en STAGING. |
| RND → TRN → FEN | El equipo reúne ambas pruebas y preparación de ficha; no hay secuencia obligatoria implementada | No encadenar creación ni imponer RND antes de TRN automáticamente. |

### Primer cambio acotado propuesto

Dos accesos nativos en el área de botones inteligentes de la revisión:
- **Orden de reparación**, solo si `repair_id` existe: abre esa orden en pantalla completa.
- **Equipo**, si `lot_id` existe: abre esa serie en pantalla completa.

Se nombran destinos, no «siguiente paso» ni «volver»: funcionan aunque el usuario
no haya pasado antes por esos registros. Se conserva la cabecera de Confirmar / Imprimir
ficha y no se crea panel, porcentaje, contador de tareas ni estados nuevos.
No cambiar datos, confirmar, emitir ni crear al navegar. Guardado y descarte deben
seguir el comportamiento nativo. Sin sudo; acceso sujeto a permisos reales del destino.
No prometer apertura de una pestaña específica sin verificar la API del cliente Odoo.

Aprobado por el usuario el 2026-10-07. Implementación local: dos acciones de lectura
con comprobación de acceso, botones inteligentes nativos visibles solo con vínculo,
sin cambiar procesos ni documentos PDF. RED comprobado en STAGING: métodos ausentes
en los ocho subcasos de tres pruebas. GREEN confirmado en STAGING: tres pruebas
focalizadas y 352 de suite completa sin fallos/errores; rutas reales de los tres tipos
verificadas con rollback y QWeb PDF intactos. QA visual comprobada el 2026-10-07:
REV/00022 abre orden WH/RO/00019 y serie 0000008; rendimiento histórico REV/00020
y TRN/00003 ocultan Orden de reparación y abren sus equipos. Se conserva la ruta
superior para volver; sin editar datos ni renumerar documentos históricos.
Después se comprobará retomar FEN existente; no añadir más botones por anticipación.

### Pruebas necesarias para este tramo

- REV vinculada abre su orden exacta; RND/TRN sin reparación no muestran ese acceso.
- Equipo exacto accesible desde cada tipo; no elevar permisos ni revelar registros inaccesibles.
- Entrada desde menú independiente y desde orden/equipo: mismo destino.
- Guardar, cancelar guardado y validación de datos pendientes: navegación sin pérdida de datos.
- Confirmadas siguen consultables, sin desbloquear edición ni cambiar resultados.
- Abrir una relación no crea otra revisión/FEN ni altera referencias o PDFs.

### Casos por completar en STAGING

MO sin serie / varias series; equipo sin MO; revisión confirmada; usuarios con
permisos reducidos; FEN borrador/emitida y retorno a su equipo; entrega nativa según
Ventas/Inventario/Alquiler. Diseño/BOM, repuestos y re-test siguen siendo condicionales,
no pasos universales. No transformar datos ausentes en obligaciones nuevas.

## 1. Qué queremos resolver

Una persona debe saber qué hacer y cómo continuar desde el registro que está usando,
sin memorizar aplicaciones ni pestañas. Abrir el registro correcto es una parte;
llegar al apartado donde se trabaja también importa.

El éxito se comprueba recorriendo una reparación y una aceptación de equipo nuevo:
la persona entiende la tarea, encuentra la acción, conserva sus datos y puede volver
al registro de origen sin buscar manualmente el equipo o la orden.

No se crea un proceso paralelo ni un estado manual de avance. Se conservan los estados,
relaciones y validaciones actuales. No se modifican PDFs, presupuesto adaptativo,
catálogos, permisos ni reglas de entrega en esta etapa. Centro de trabajo posterior.

## 2. Qué prueba esta auditoría y qué no

- **Comprobado en código:** campos, acciones y condiciones descritos abajo.
- **Hipótesis de usabilidad:** un enlace existente puede ser poco visible. No equivale
  a demostrar que el usuario se pierde ni a justificar otro botón automáticamente.
- **Pendiente de pantalla:** formulario combinado de Odoo, personalizaciones, acciones
  nativas, comportamiento de guardado y apertura de pestañas.
- **Pendiente de taller:** orden real de tareas, responsables y excepciones del proceso.

Las propuestas se implementan solo donde la comprobación encuentre una dificultad real.
No convertir documentación antigua ni comentarios de código en evidencia de pantalla.

## 3. Reparación: recorrido vigente

| Momento | Conexión comprobada | Evaluación / límite |
| --- | --- | --- |
| Recepción | Orden con serie, síntomas, sospechas y equipos recibidos | La pestaña existe. Comprobar si basta su organización o hace falta orientación visible. |
| Entrada al taller | Al salir de draft hacia un estado distinto de draft/cancel, se crea una REV de reparación para un ROV si la visita no tiene otra | Se crea la revisión, pero esa operación no devuelve una acción para abrirla. No crear revisiones por navegar. |
| Diagnóstico | Lista de revisiones de la visita con Editar/Abrir; acceso al historial completo del equipo | Abrir ya existe. Evaluar visibilidad antes de añadir Continuar revisión. Historial del equipo y revisión de esta visita no son intercambiables. |
| Trabajos y repuestos | Pestañas Trabajos realizados y Repuestos | El registro vuelve a ser la orden. La revisión tiene enlace Many2one a ella; falta comprobar si el retorno resulta evidente. |
| Verificación del resultado | Nueva revisión crea otro pase de la visita; motivo distingue re-test y comparación | Crear otra prueba es una decisión. No deducir que todo trabajo exige re-test ni reutilizar un diagnóstico como verificación final. |
| Ficha reparada | Imprimir ficha propone la reparación más reciente por fecha/id de la visita; el wizard permite cambiarla | Una propuesta reciente no identifica por sí sola el pase final. Conservar selección visible y mostrar contexto de la revisión. |
| Cierre | Exige tipo de intervención, origen de trabajos y al menos un repuesto si alguna acción lo consume; sella fecha si falta | Revisión en borrador no bloquea. No añadir restricciones nuevas para representar el recorrido. Cierre de orden y entrega física no deben confundirse. |

Una visita de diagnóstico sin trabajos puede cerrarse. Las etapas son orientación,
no un checklist obligatorio idéntico para todas las órdenes.

Fuentes: [orden](../../models/repair_order.py), [vista de orden](../../views/repair_order_views.xml),
[revisión](../../models/mc_rov_revision.py), [vista de revisión](../../views/mc_rov_revision_views.xml),
[asistente de impresión](../../wizards/mc_rov_ficha_wizard.py).

## 4. Fabricación y aceptación: recorrido vigente

| Momento | Conexión comprobada | Evaluación / límite |
| --- | --- | --- |
| Fabricar | MO nativa y lecciones del modelo; al terminar, series producidas se añaden a alertas sin alcance | mc_rov no aporta botón MO → equipo. Comprobar enlaces nativos antes de construirlo. No afirmar que la serie nace exclusivamente al finalizar. |
| Configurar | Serie con Especificaciones y aviso de datos faltantes | La ficha técnica registra lo que el equipo es. El software puede precargarse y completarse desde RND; no ordenar dejarlo vacío. |
| Rendimiento | Nueva prueba de rendimiento crea una RND del equipo | Siempre crea. Diferenciar iniciar otro intento de continuar uno ya abierto. |
| Terreno | Nueva prueba en terreno crea TRN; historial común por equipo | No hay acción propia RND → TRN. La secuencia de trabajo debe validarse; no imponer bloqueo ni iniciar terreno automáticamente al confirmar RND. |
| Preparar FEN | Imprimir ficha abre wizard; propone pruebas del equipo/tipo correcto, sin reparación, entre borradores y confirmadas aceptadas | Preparar desde este botón puede crear otra ficha al guardar/emitir. Retomar una FEN existente debe abrir su registro, no repetir la creación. |
| Emitir FEN | Requiere RND y TRN confirmadas y aprobadas o aprobadas con observaciones; guarda PDF final | Vista previa no es emisión. FEN emitida conserva documento y referencias aunque aparezcan revisiones nuevas. |
| Entregar | Operaciones nativas de Inventario/Ventas/Alquiler | No se encontró en mc_rov un bloqueo de entrega por RND/TRN/FEN. Su existencia en personalizaciones y su conveniencia son asuntos distintos. |

Una MO puede producir varias series: si se agrega navegación, una abre formulario y
varias abren una lista limitada a esas series; nunca elegir silenciosamente la primera.
También hay equipos anteriores al sistema, sin MO en Odoo: aceptación debe seguir
siendo accesible desde la serie, sin exigir fabricación registrada.

No se incorpora una batería de controles de armado: el diseño previo la descartó.
Odoo admite controles de calidad configurados, pero no se asume su contenido ni que
haya una batería operativa instalada. Verificar la configuración real con taller.

Fuentes: [fabricación](../../models/mrp_production.py), [vista MO](../../views/mrp_production_views.xml),
[equipo](../../models/stock_lot.py), [vista equipo](../../views/stock_lot_views.xml),
[FEN](../../models/mc_rov_ficha_equipo_nuevo.py),
[asistente FEN](../../wizards/mc_rov_ficha_equipo_nuevo_wizard.py).

## 5. Reglas de navegación que deben quedar explícitas

1. **Continuar abre; Nueva crea.** No cambiar silenciosamente las acciones actuales
   Nueva revisión / Nueva prueba. Si existe borrador, ofrecer retomarlo separadamente.
2. **Cero, uno o varios candidatos:** cero explica qué falta; uno puede abrirse directo;
   varios requieren selección con referencia, fecha, tipo, estado, responsable y motivo
   cuando exista. No reducir ambiguamente todo el historial a «la última».
3. **Ámbito preciso:** una orden retoma sus revisiones de reparación; RND/TRN de aceptación
   pertenecen a la serie y no a una reparación. FEN retoma fichas de esa serie.
4. **Confirmado no significa aprobado.** Un rechazado sigue visible en el historial;
   un borrador no tiene veredicto. No anunciar «listo para entregar» desde un conteo.
5. **Último intento y evidencia seleccionable son distintos.** FEN excluye confirmadas
   rechazadas y propone la candidata más reciente elegible. La guía no debe ocultar que
   hay un intento posterior rechazado ni cambiar por sí sola la selección aprobada.
6. **Navegar no altera negocio:** no confirma pruebas, cierra órdenes, emite FEN,
   cambia propietarios ni crea series. El guardado normal del formulario sigue aplicando.
7. **Guardar y volver:** comprobar cambios sin guardar, validaciones y cancelación.
   Un botón Volver no puede perder datos ni desviar al equipo/orden equivocado.
8. **Pestaña de destino:** no dar por válido un contexto inventado. Verificar el soporte
   del cliente Odoo 19. Si abrir solo el registro deja la tarea escondida, el enlace no
   se considera solución completa; evaluar acceso directo al apartado sin rediseño global.
9. **ROV/no-ROV y permisos:** ocultar guía específica en otros equipos y respetar los
   permisos existentes. No usar sudo para que un enlace funcione.

## 6. Propuesta acotada, por orden de trabajo

### A. Validar dos recorridos antes de añadir botones

Recorrer en STAGING una visita de reparación y una MO/aceptación. Registrar:
registro de partida, tarea, acción actual, destino, pestaña y dónde se necesita ayuda.
Incluir retomar un trabajo a medias y un equipo sin MO. Reparación es el piloto
recomendado, no una prioridad ya confirmada por el usuario.

### B. Resolver los cortes comprobados

Candidatos, sujetos al recorrido de pantalla:
- **Continuar revisión** en la orden, solo si mejora el acceso Editar/Abrir existente.
- **Abrir orden de reparación** desde REV y **Abrir equipo** desde revisiones/FEN:
  destinos explícitos, no dependientes de haber llegado desde una pantalla concreta.
- **Abrir equipo / Ver equipos producidos** desde MO si la acción nativa no resuelve el paso.
- Accesos para retomar RND, TRN o FEN en borrador desde el equipo cuando el historial
  no permita hacerlo con claridad. Reutilizar las listas y formularios existentes.

No añadir todos estos botones por defecto. Mantener una acción principal clara y los
accesos secundarios agrupados; evitar una cabecera llena de acciones equivalentes.

### C. Orientación dentro del registro

Mostrar tarea y faltantes relevantes, con acceso al apartado donde se resuelven.
No solo enlaces entre módulos: Recepción, Revisiones, Trabajos, Repuestos y Cierre
necesitan también continuidad dentro de la orden.

Reutilizar el aviso de ficha incompleta y los criterios actuales de confirmación/cierre.
Si se muestran requisitos antes de actuar, la validación y el aviso deben compartir
la misma regla, sin duplicar cálculos que puedan discrepar. No poner todas las tareas
bajo «Pendiente»: distinguir requisito bloqueante, advertencia y paso opcional.

### D. Centro de trabajo, después

Con los recorridos validados, reunir tareas operativas y accesos por proceso. Sin
indicadores de desempeño ni cambios de permisos, carga o pipeline en esta etapa.

## 7. Validación y criterio de aceptación

### Guion de comprobación en pantalla

Usar registros existentes, sin crear revisiones, emitir fichas ni cambiar estados.
Abrir selectores y cancelarlos cuando sea necesario comprobar una propuesta.

| Recorrido | Comprobación concreta |
| --- | --- |
| Orden → REV | Desde Revisiones, abrir un pase de esta visita y comprobar si su estado, resultado y motivo permiten reconocer cuál retomar. |
| REV → orden | Comprobar el enlace a la orden y cómo regresar a Trabajos realizados o Repuestos sin buscarla nuevamente. |
| Orden → ficha | Abrir Imprimir ficha, comprobar propuesta y opciones de esta visita; cancelar. No confundir reciente con re-test final. |
| Orden → cierre | Leer avisos y campos de Cierre sin ejecutar el cierre; contrastar requisitos con las reglas auditadas. |
| MO → serie | Buscar primero el acceso nativo al equipo producido, incluyendo el caso de varias series. |
| Serie → configuración | Comprobar dónde se completan Especificaciones y cómo se reconocen los datos faltantes. |
| Serie → RND/TRN | Abrir revisiones existentes desde Pruebas; distinguir retomar de Nueva prueba y comprobar retorno al equipo. |
| Serie → FEN | Abrir una ficha existente y comprobar acceso a sus evidencias. Revisar el selector sin guardar otra ficha. |

Por cada paso registrar: registro usado, acción visible, destino/pestaña, dificultad
observada y evidencia. Marcar lo que no pudo probarse; no completar el resultado
por inferencia del código. Priorizar pérdida de contexto, creación accidental de
duplicados y dificultad para retomar antes de añadir accesos meramente convenientes.

| Caso | Resultado esperado |
| --- | --- |
| REV: cero / una / varias revisiones pendientes | Mensaje, acceso directo o selección; ninguna creación al continuar. |
| REV: diagnóstico sin trabajos / reparación con re-test | Ambos recorridos posibles; motivo y pase elegido visibles. |
| Revisión rechazada / borrador / confirmada aceptada | Estado y resultado no se confunden; no cerrar ni aprobar al navegar. |
| MO: sin serie / una / varias / producto no ROV | Orientación o destino preciso; no inventar series ni mostrar guía ROV fuera de alcance. |
| Equipo sin MO | Configuración y aceptación accesibles desde la serie. |
| RND/TRN: varios intentos, tipos/equipos distintos | Continuación sin duplicar ni mezclar; intentos rechazados permanecen consultables. |
| FEN: borrador existente / emitida / pruebas ausentes | Retomar sin crear otra; vista previa permitida; emisión conserva sus bloqueos. |
| Cambios sin guardar / formulario inválido / cancelación | Sin pérdida de datos ni navegación engañosa. |
| Usuario sin acceso al destino | Respeto de permisos y explicación; sin elevación de privilegios. |

La QA incluye navegador, además de pruebas de acciones y dominios. No basta comprobar
que un método devuelve una acción: hay que demostrar que el usuario llega donde trabaja.
Los PDF y su composición quedan fuera del cambio; confirmar que sus rutas no se alteraron.

## 8. Primer recorrido real de STAGING — 2026-10-05

Sesión administrativa; inspección de registros existentes, sin editar campos,
confirmar revisiones, cerrar órdenes ni guardar/emitir FEN. Se abrieron dos
asistentes y se cancelaron. Esto valida accesos de estas muestras, no todos los
perfiles, dominios ni escenarios de la matriz anterior.

| Muestra / paso | Resultado observado | Consecuencia para la propuesta |
| --- | --- | --- |
| WH/RO/00019 → Revisiones | Lista con REV/00022, REV/00019 y REV/00016, todas en borrador; Editar disponible | Retomar ya está resuelto técnicamente. No añadir otro botón equivalente por defecto. |
| Editar REV/00022 | Abre formulario completo; motivo Primer diagnóstico y enlace interno a la orden visibles | Hay contexto de la visita. El motivo no figura en la lista de la orden, por lo que allí cuesta distinguir pases sin abrirlos. |
| REV/00022 → WH/RO/00019 | La ruta superior vuelve a la orden; Trabajos realizados se abre después | No hay un corte entre registros. La tarea siguiente y su pestaña siguen dependiendo del conocimiento del usuario. |
| Orden → Imprimir ficha | Propone REV/00022 y permite escoger; asistente cancelado | La propuesta reciente funciona; no acredita que sea la verificación final. |
| Orden → Cierre | Fecha de entrega, análisis de origen y texto al cliente visibles | Ya hay explicación del origen. No se probó ejecutar cierre; la orden está Reparado pese a sus revisiones en borrador. No inventar un bloqueo nuevo. |
| WH/MO/00011 | Por cerrar, sin serie seleccionada | No permite comprobar continuidad a un equipo producido; no generar una serie durante la auditoría. |
| WH/MO/00010 → Números de serie | Botón nativo abre lista con 0000008; la fila abre el equipo | El enlace nativo existe y funciona, incluso si una sola serie requiere abrir la fila. No añadir Abrir equipo duplicado sin justificarlo. |
| Equipo 0000008 → Especificaciones / Pruebas | Configuración accesible; Pruebas mezcla reparaciones, rendimiento y terreno, con Editar/Abrir por fila | Separar orientación de aceptación del historial general; no eliminar registros históricos. |
| Equipo → Editar REV/00020 | Abre Prueba de rendimiento existente; ruta superior conserva enlace al equipo | No es necesario crear otra RND para continuar. Los botones Nueva prueba destacan más que la continuación del historial. |
| Equipo → Editar REV/00021 → equipo | Abre Prueba en terreno existente y el enlace superior permite regresar al equipo | Continuar TRN también funciona sin crear otra revisión. |
| Equipo → Imprimir ficha | Propone rendimiento REV/00020 y terreno REV/00021; aviso diferencia borrador de emisión; cancelado | Selección por tipo funciona en esta muestra. Los prefijos históricos REV no significan tipo Reparación. |
| Historial FEN de 0000008 | Vacío | Retomar una FEN existente no se pudo probar en este equipo; queda pendiente, no marcarlo validado. |
| Inventario → series → 26-02 → FEN/00878 | La fila FEN abre un formulario modal de la ficha existente, con Vista previa, Emitir ficha y enlace a TRN/00003; RND ausente | Retomar existe, pero queda debajo del historial de pruebas. La guía debe señalar la ficha existente y sus evidencias ausentes, sin guardar otra. Modal cerrado sin cambios. |
| Equipo 26-02 fuera del contexto MO | Especificaciones, Pruebas y FEN accesibles desde Inventario; aviso enumera cuatro datos técnicos faltantes | La aceptación es accesible sin entrar desde fabricación. No se ha demostrado que este equipo carezca de MO; solo que esta ruta no la necesita. |

**Primera mejora recomendada:** orientación dentro de la orden y del equipo, antes
de sumar enlaces entre módulos. En reparación, hacer visibles los pases y su motivo
y ofrecer acceso al apartado de trabajo correspondiente. En aceptación, mostrar
RND, TRN y FEN como tareas diferenciadas con estado y resultado, priorizando retomar
borradores existentes sobre crear otra prueba. No declarar un único siguiente paso
cuando existan varias revisiones o cuando taller deba decidir si corresponde re-test.

Pendiente de QA: equipo realmente sin MO, varias series,
usuario de taller con permisos habituales y navegación con cambios sin guardar.
La muestra no permite evaluar esos casos ni definir por sí sola el orden de taller.

## 9. Propuesta de primer piloto para revisar con taller

Un panel compacto de **Guía de trabajo** en la columna del chatter, encima de
mensajes y actividades, dentro de la orden ROV y del equipo ROV. Dirección visual
elegida durante la revisión de la maqueta; integración real en Odoo aún pendiente.
No una barra de etapas que declare el proceso completo o imponga un orden rígido.
Tareas expresadas en lenguaje de taller, con acceso al registro o apartado actual.
Los historiales, botones actuales y estados de Odoo se conservan.

### Orden de reparación

| Tarea visible | Información / acceso propuesto |
| --- | --- |
| Revisar recepción | Abrir Recepción. No marcarla completa por rellenar un campo opcional. |
| Retomar revisión de esta visita | Mostrar cantidad de borradores y contexto de pases; con uno, abrirlo; con varios, mostrar selección de esta visita con fecha, motivo, responsable, estado y resultado. Sin borradores, consultar revisiones; crear otra sigue siendo decisión explícita. |
| Registrar trabajos y repuestos | Acceder a las pestañas correspondientes. No inferir que toda visita requiere trabajos: diagnóstico sin reparación es válido. |
| Preparar ficha y cierre | Acceder al selector actual y a Cierre. Mostrar requisitos bloqueantes de las validaciones existentes por separado de avisos; revisión pendiente no se convierte en nuevo bloqueo. |

Añadir Motivo a la lista de revisiones de la visita facilita distinguir diagnóstico,
re-test y comparación sin abrir cada fila. No elegir automáticamente el re-test final.
Desde REV, conservar retorno nativo y ofrecer acceso explícito a Trabajos de su orden
solo si la guía necesita llevar a esa pestaña; no duplicar un simple enlace a la orden.

### Equipo: configuración y aceptación

| Tarea visible | Información / acceso propuesto |
| --- | --- |
| Completar configuración | Reutilizar aviso y lista de faltantes de ficha técnica; acceso a Especificaciones. No calcular otra definición de ficha completa. |
| Rendimiento | Distinguir borradores, confirmadas aceptadas y rechazadas; retomar o consultar pruebas de este equipo y tipo, sin reparación asociada. Nueva prueba es acción secundaria explícita. |
| Terreno | Misma regla que rendimiento, con su tipo propio. No exigir secuencia RND antes de TRN sin decisión de taller. |
| Ficha de equipo nuevo | Priorizar fichas existentes: retomar borrador o consultar emitida. Con varias, selección visible; preparar nueva conserva el asistente actual y sus reglas. Mostrar qué evidencia falta en el borrador consultado, sin sustituir sus referencias automáticamente. |

Con cero registros, explicar que todavía no existe la prueba/ficha; con uno, abrir
directamente; con varios, mostrar selección contextual. Continuar nunca crea registros.
No representar una aceptación completa por contar RND/TRN: resultado, estado y
referencias explícitas de la FEN siguen mandando. FEN emitida permanece congelada.

### Alcance y comprobación del piloto

Primero reparación; luego la misma pauta de orientación para equipo/aceptación.
No añadir un botón MO → equipo: el acceso nativo ya está comprobado para una serie.
Probar varias series si existe una muestra; si no, cubrir acción/domino con pruebas
al implementar y registrar la limitación de QA, sin fabricar evidencia de pantalla.

No cambiar modelos de documentos, PDFs, estados, permisos ni reglas comerciales.
Las pruebas de implementación deben cubrir selección cero/uno/varios, contexto de
visita/tipo/equipo y ausencia de creación al continuar. La apertura efectiva de
pestaña y el guardado requieren QA de navegador; no afirmar que funcionan mediante
un contexto XML supuesto. Validar un usuario habitual de taller antes del despliegue,
sin cambiar permisos como parte de este piloto.

Esta propuesta todavía no está implementada. La revisión con taller debe confirmar
que los nombres y accesos reflejan tareas reales antes de definir detalles de interfaz.

## 10. Aplicabilidad, ubicación y conteos de la guía

Antes de implementar, clasificar cada tarea como requisito de una acción concreta,
condicional, recomendación u opción. No convertir el recorrido orientativo en una
lista universal de obligaciones. La existencia de un enlace no demuestra que el paso
sea necesario; la ausencia de un documento tampoco implica un pendiente obligatorio.

| Proceso / tarea | Criterio de aplicabilidad |
| --- | --- |
| Fabricación con diseño vigente | Utilizar la configuración y BoM que correspondan al trabajo. No exigir actualizar la BoM ni crear una orden de cambio para cada fabricación. |
| Cambio de diseño / BoM | Rama condicional cuando realmente cambia el diseño; confirmar con taller el procedimiento de PLM aplicable. No generar ECO automáticamente por fabricar o reparar. |
| Controles de fabricación | Dependen de los controles configurados y del producto/operación. No inventar una batería universal ni marcar pruebas inexistentes como tareas incumplidas. |
| Configuración del equipo | Mostrar los faltantes que ya calcula el sistema como orientación. No transformarlos en bloqueos adicionales de fabricación, aceptación o entrega. |
| RND / TRN | Evidencias requeridas para emitir FEN según las reglas actuales; no declarar que bloquean por sí mismas el cierre de MO o la entrega comercial. Repetición según necesidad, sin imponer un único intento ni un orden nuevo. |
| Preparar FEN | Puede iniciarse como borrador con evidencia incompleta. Emitir exige las dos revisiones seleccionadas confirmadas y aceptadas. Consultar una FEN emitida no requiere otra emisión. |
| Reparación: recepción / diagnóstico | Orientar hacia los datos y revisiones existentes. Los campos opcionales de recepción siguen siendo opcionales. |
| Reparación: trabajos / repuestos | Condicionales a lo que se hizo. Con trabajos registrados, respetar requisitos de origen; con acciones que consumen repuestos, respetar su validación existente. No exigir trabajos para un diagnóstico sin intervención. |
| Reparación: re-test | Decisión de taller según intervención y resultado. No añadir un bloqueo general por revisión en borrador ni imponer re-test a toda visita. |
| Reparación: cierre | El tipo de intervención es requisito actual de cierre. Origen y repuestos dependen de los trabajos registrados; una revisión en borrador no se convierte en bloqueo nuevo. |
| Calidad / lección / cambio de diseño | Ramas condicionales a una incidencia y al análisis aplicable. No exigir alerta, lección o ECO para cada orden. |

Esta tabla distingue reglas comprobadas de decisiones de taller pendientes; no
certifica todas las combinaciones del ERP. Para cerrar la aplicabilidad, contrastar
cada rama con código, una muestra de pantalla y el responsable del proceso. Añadir
casos sin cambios de diseño, diagnóstico sin intervención, prueba repetida, evidencia
rechazada y equipo sin contexto de MO a la revisión con taller.

### Ubicación y lectura visual propuestas

Ubicar **Guía de trabajo** encima del chatter, compartiendo su columna derecha:
formulario a la izquierda, guía y chatter apilados a la derecha. Dos columnas,
sin panel superpuesto ni tercera columna. En la orden para reparación y en la serie
para configuración/aceptación. La propuesta inicial antes de pestañas se descartó
porque desplaza el trabajo; la nueva maqueta B representa esta decisión. En MO, aprovechar primero
los accesos nativos y añadir orientación solo donde la auditoría demuestre una dificultad.

La guía inicia visible y tiene botón Ocultar/Mostrar. Al ocultarla permanece su
cabecera y el chatter recupera espacio; cambiar pestaña no cambia esta preferencia.
No ocultar alertas importantes dentro de la guía. En ancho estrecho, la maqueta apila
formulario y columna auxiliar; el comportamiento definitivo debe contrastarse con
la recolocación nativa del chatter de Odoo y no reducir artificialmente el formulario.

Cada fila tendrá tarea, situación concreta y una acción para abrir el destino. Por
ejemplo: «Rendimiento — sin prueba registrada — Ver / iniciar prueba» o «Ficha de
equipo nuevo — borrador existente; falta RND válida — Retomar ficha». La creación
seguirá siendo una acción explícita; abrir la guía o continuar no creará documentos.

Mostrar recomendaciones y ramas opcionales en **Otras acciones**, sin tratarlas como
errores. Un requisito bloqueante debe indicar para qué acción lo es, por ejemplo
**Falta RND válida para emitir esta ficha**, evitando un genérico «Equipo incompleto».
No usar un porcentaje de avance ni una secuencia numerada obligatoria antes de
resolver aplicabilidad y responsabilidades.

Los números expresarán registros o faltantes verificables: «3 revisiones en borrador»,
«4 datos de configuración faltantes» o «1 ficha en borrador». No sumarlos como cinco
tareas obligatorias: pueden pertenecer a intentos anteriores, ser recomendaciones
o bloquear acciones distintas. Revisar también el caso de pruebas históricas frente
a evidencia seleccionada para la FEN antes de llamar a una revisión «pendiente».

El futuro **Centro de trabajo ROV** será la entrada central para encontrar y retomar
registros. Abrirá estas mismas guías en su contexto y reutilizará sus criterios de
aplicabilidad; no mantendrá otra definición de pendiente ni otro proceso paralelo.
Los conteos personales por responsable requieren definir asignación y permisos antes
de presentarlos como «Mis tareas».

### Maqueta local de revisión — 2026-10-05

Prototipo descartable en `../.tmp/flujo-guiado-prototype/index.html`, sin conexión a
Odoo, sin escrituras ni persistencia. Representa un formulario simplificado, no una
captura del Odoo instalado. Los casos y números son ejemplos para revisar la interfaz,
no una consulta del estado vivo de las órdenes. La franja amarilla y el selector de
diseño son controles del prototipo y no se implementarían en el producto.

Tres alternativas, con la misma aplicabilidad: A, panel antes de pestañas; B, guía
lateral; C, resumen desplegable. A fue la recomendación inicial, pero el usuario
señaló que un panel intermedio distrae y desplaza el trabajo. C comparte esa ubicación.
B se corrigió para incluir el chatter que faltaba en la primera maqueta; guía plegable
arriba, chatter debajo, dentro de la misma columna. El usuario acepta esta dirección.
No implica aprobación de una integración técnica que todavía no existe.

Casos disponibles: diagnóstico sin intervención, varios pases, cambio sin repuesto,
verificación disponible; FEN incompleta, pruebas aceptadas, intento repetido y ficha
emitida; fabricación con diseño vigente, cambio de diseño y varias series. Las ramas
de diseño y controles configurados son hipótesis de aplicabilidad que taller debe
validar, no reglas nuevas ni verificaciones completas de fabricación nativa.

Comprobado en el navegador del prototipo: acceso a Trabajos realizados, selector de
varios pases, apertura simulada del borrador FEN, separación de requisitos de emisión,
BoM fuera de pendientes en diseño vigente y cambio entre las tres ubicaciones. Esto
valida la maqueta, no el guardado, los permisos ni la navegación real futura de Odoo.
En B revisada se comprobó además Ocultar/Mostrar, chatter visible con guía oculta y
estado de apertura conservado al cambiar pestaña. Captura de referencia local:
`../.tmp/flujo-guiado-prototype/guia-chatter.jpg`. El límite de altura del listado con
scroll pertenece solo al prototipo; no define alturas del formulario productivo.

## 11. Decisiones que faltan, sin bloquear la auditoría

- Quién realiza recepción, diagnóstico, reparación, re-test y aceptación en taller.
- Qué tareas se repiten y quién decide qué revisión acompaña la entrega.
- Qué acceso nativo de MO funciona realmente y cuándo se asignan las series.
- Si la entrega comercial necesita controles adicionales: decisión posterior, no asumida.
- Qué enlaces necesitan apertura de pestaña y cuáles ya funcionan con navegación nativa.

La lista anterior ordena la comprobación; no propone campos obligatorios nuevos.

## 12. Auditoría de FEN y fabricación — 2026-10-07

Consulta de solo lectura de STAGING y navegación sin guardar ni ejecutar acciones
de negocio. El shell terminó con rollback; no se crearon fichas, series o controles,
no se consumieron correlativos ni se reinició el servicio. Evidencia local:
`../.tmp/process-navigation-audit/inventory.json` y `../.tmp/fen-navigation-qa`.
Los archivos de evidencia no forman parte del módulo.

### Conexiones y límites comprobados

| Caso | Evidencia actual | Resultado / siguiente comprobación |
| --- | --- | --- |
| Retomar FEN en borrador | Pantalla: 26-02 → Pruebas → FEN/00878 → Expandir | Abre el registro existente con Vista previa / Emitir ficha; permite volver al equipo. La apertura inicial es un modal de consulta. |
| Consultar FEN emitida | Código del modelo; cero emitidas en STAGING | La descarga utiliza el adjunto final almacenado. Falta QA de pantalla con una ficha emitida; no emitir un documento de cliente para probarlo. |
| Varias FEN del mismo equipo | Lista relacional existente; una sola FEN en toda la muestra | No hay muestra para comprobar elección/retorno con varias. No afirmar que el encabezado Imprimir ficha retoma una existente: abre el asistente para preparar otra. |
| Entrada general a FEN | Vistas locales | No hay menú general de fichas. El acceso actual es desde el equipo. Evaluar necesidad antes de añadir otro acceso. |
| Fabricación sin serie | Pantalla WH/MO/00011, estado Por cerrar | Campo Número de serie/lote disponible; Números de serie oculto. No se pulsó generar ni producir. |
| Fabricación con una serie | WH/MO/00010 → serie 0000008, recorrido ya comprobado | Acceso nativo suficiente; no añadir un botón equivalente. |
| Fabricación con varias series | Código instalado: acción con dominio sobre todos los lot_producing_ids | La acción abre una lista restringida a las unidades de la MO, no elige silenciosamente la primera. Falta muestra de pantalla; las 11 MO inventariadas no tienen varias series. |
| Controles de fabricación configurados | Código instalado: check_quality abre controles pendientes de esa MO | Ninguna de las 11 MO tiene check_ids. Falta validar una operación con controles configurados; ausencia de controles no equivale a incumplimiento. |
| Cambio de diseño | Código PLM: crear ECO requiere BoM; acceso condicionado a ECO existentes | Rama condicional. No exigir ECO ni actualización de BoM por fabricar; procedimiento real por confirmar con taller. |

La cantidad del botón de series se calcula con `lot_producing_ids` y solo para
productos con seguimiento por serie. No inferir a partir de ese botón la trazabilidad
completa de movimientos históricos ni declarar inválida una MO antigua sin series.
Generar una serie sí crea datos: no es una acción de navegación ni se ejecutó en QA.

### Aplicabilidad del recorrido

| Paso | Clase y alcance |
| --- | --- |
| Fabricar con diseño vigente | Usar la BoM/configuración que corresponda; modificar el diseño es opcional salvo cambio real. |
| Asignar serie | Depende del seguimiento del producto. Necesaria para identificar la unidad que respalda configuración, pruebas y FEN; no imponerla a productos sin seguimiento. |
| Controles de armado | Condicionales a producto/operación y controles configurados. No duplicar aquí mediciones de RND/TRN. |
| Completar especificaciones | Recomendación con el aviso de faltantes existente; no crear un bloqueo universal de MO. |
| Realizar/repetir RND y TRN | Validaciones independientes del equipo. Repetir según necesidad; el sistema no debe imponer un orden nuevo entre ambas. |
| Preparar FEN | Admite borrador y vista previa con evidencia incompleta. Las pruebas elegidas permanecen visibles. |
| Emitir FEN | Requisito de esta acción: RND y TRN seleccionadas del mismo equipo, del tipo correcto, sin reparación asociada, confirmadas y aceptadas. No trasladar ese requisito a cerrar MO o entregar comercialmente. |
| Consultar una emitida | Abrir el documento almacenado; no preparar otra ni cambiar automáticamente su evidencia por pruebas posteriores. |
| Entrega comercial | Responsabilidades y controles por definir con taller/comercial; no derivar un bloqueo de la ausencia de FEN sin una decisión de negocio. |

### Cortes y decisiones siguientes

El principal punto de fricción observado es **retomar FEN**: la fila abre un modal y
hay que reconocer Expandir para llegar al formulario con las acciones. El encabezado
Imprimir ficha prepara un nuevo documento y no sustituye ese recorrido. Antes de
programar, evaluar un acceso explícito Abrir/Retomar en la lista existente; no añadir
un panel que repita pestañas ni una selección automática de la última ficha.

Para cerrar QA faltan muestras de FEN emitida, varias FEN/series y controles
configurados. Preferir registros existentes; si se acuerdan fixtures, usar nombres
explícitos y rollback, sin secuencias ni emisiones de cliente. Los casos respaldados
solo por código no se presentan como comprobados en navegador.

Con taller queda confirmar quién asigna series, quién decide repetir/seleccionar
pruebas y cómo se enlaza aceptación con entrega. El centro de trabajo vendrá después:
debe retomar estos mismos registros y reglas, sin inventar otra definición de pendiente.

## 13. Mapa de relaciones y escenarios aprobado — 2026-10-07

El usuario confirma que los recorridos permiten comenzar en distintos registros,
continuar o no y tomar ramas según la situación. No son una secuencia de tareas
obligatorias. Escenarios y destinos se mantienen en [Flujo de trabajo](../flujo-de-trabajo.md),
apartados Cómo leer los recorridos, Relaciones y Calidad.

Separar fabricación repetida, modelo nuevo, variante/cambio y reparación con o sin
mejora. Calidad e ingeniería son procedimientos anexos: una incidencia puede requerir
prevención desde el primer caso; una mejora solicitada puede requerir ingeniería sin
incidencia. No crear alerta o ECO automáticamente al navegar ni imponerlos a cada orden.

El acuerdo conceptual no certifica accesos no auditados ni define nuevas reglas de
desarrollo/aprobación. Queda por verificar:

- Equipo → fabricación: relación real con las series, cardinalidad y acción nativa.
- Calidad → origen: control/orden de fabricación o reparación y unidades afectadas;
  distinguir colección de alertas de consulta del registro de origen.
- FEN → equipo y evidencia seleccionada: apertura efectiva de referencias y retorno;
  mantener los casos pendientes de emitida y varias fichas del § 12.
- Producto/BoM/ingeniería: accesos nativos, tratamiento real de variantes y vínculo
  con fabricación de validación. No inferir qué revisión de BoM se usó por ser la actual.
- Mejora desde reparación: existe la ruta por lección/alerta cuando hay incidencia;
  no se ha diseñado un vínculo directo para una mejora sin incidencia. Definirlo solo
  si se confirma un corte real, sin forzar el paso por Calidad.

Priorizar lectura de código/vistas instaladas y QA con registros existentes. No añadir
botones antes de demostrar la dificultad. El centro de trabajo reutilizará estas
relaciones y criterios; no sustituirá los accesos contextuales ni creará otro proceso.

### Resultado de la sonda de relaciones instaladas

Evidencia: `../.tmp/process-navigation-audit/relations.json`, consulta con rollback.
Se inspeccionaron relaciones ORM y formularios combinados; no se deduce apertura
efectiva ni permisos de taller únicamente por encontrar un campo en una vista.

| Enlace | Hallazgo en STAGING | Estado |
| --- | --- | --- |
| Equipo → fabricación | Sin botón directo a MO, pero serie 0000008 → Trazabilidad → WH/MO/00010 abre la fabricación exacta. | Recorrido nativo comprobado en pantalla. No hace falta agregar un botón para resolver un vínculo ausente. No confundir fabricación del mismo producto con fabricación de esta serie. |
| Equipo → reparación / Calidad | Existen acciones nativas de reparaciones, alertas y controles, estos últimos según conteos. | Conservar y validar con datos que activen cada acceso. No duplicar pestañas. |
| Calidad → reparación / serie | La alerta tiene repair_id y lot_ids. QA00004 muestra WH/RO/00016 y serie 0000008; Enlace interno abre WH/RO/00016. | Apertura de reparación comprobada y breadcrumb a la alerta. Apertura de la etiqueta de serie aún no probada. |
| Calidad → fabricación | production_id existe en el modelo, pero no apareció entre los campos ni botones del formulario combinado inspeccionado. | Posible corte para alertas de fabricación; falta muestra vinculada y comprobar el acceso por control de origen. |
| Calidad → ingeniería | Campo mc_eco_id visible. | Relación disponible; no hay ECO en la base para QA de apertura. |
| Ingeniería → fabricación | Botón nativo Producción cuando hay production_id; la acción apunta a esa MO. | Código/vista comprobados; sin ECO existente para QA de pantalla. No implementarlo otra vez. |
| Ingeniería → BoM / lecciones | Campos BoM y botón de lecciones vinculadas disponibles. | Sin ECO existente para probar el recorrido completo. |
| Producto/modelo → BoM / fabricación / ingeniería | Accesos nativos en la vista; algunos condicionados por tipo, BoM y cantidades. La acción BoM contempla opciones de variante o plantilla. | No sustituirlos con botones genéricos. Falta QA de escenarios configurados; existencia de soporte de variantes no define el procedimiento de taller. |
| Reparación → fabricación | Existe acción nativa action_view_mrp_productions, condicionada por production_count y estado. | No asumir que representa la fabricación original de la serie: falta verificar su dominio antes de recomendarla para investigar origen. |
| FEN → equipo / RND / TRN | FEN/00878 → Enlace interno abre serie 26-02 y TRN/00003 seleccionada; retorno a FEN por breadcrumb comprobado desde TRN. | Equipo y TRN comprobados. RND está vacía en la muestra, por lo que no se certifica su apertura en pantalla. |

La muestra contiene tres alertas: dos vinculadas a reparación y todas a serie 0000008;
cero controles nativos y cero ECO. No hay una alerta vinculada a fabricación para
comprobar ese retorno en pantalla. La ausencia de registros limita QA, no demuestra
que los procesos estén deshabilitados.

En la alerta, la etiqueta nativa Equipo identifica al equipo de Calidad (Main Quality
Team), mientras Lote identifica al ROV. Tenerlo presente en instrucciones de usuario;
no confundir ese campo con el botón Equipo de las revisiones. Sin cambio de etiquetas
autorizado ni realizado en esta auditoría.

### Consistencia de conexiones — comprobación visual

El usuario pide que las conexiones se reconozcan con un patrón estándar como Equipo.
Comprobado en STAGING, sin editar: serie 0000008 tiene botones inteligentes superiores
Alertas de calidad (3) y Reparaciones (presentado como Por reparar: 2 / Hecho: 2).
El segundo abre la lista contextual de órdenes. WH/RO/00016 presenta arriba el botón
Alertas de calidad (1). No son pestañas; la pestaña duplicada de alertas en la serie
fue retirada anteriormente. Capturas en `../.tmp/process-navigation-audit`.

Mantener botones inteligentes nativos con icono/nombre y conteo si son colecciones;
Equipo y Orden de reparación identifican destinos únicos. Las pestañas organizan
contenido del registro actual; las acciones principales ejecutan operaciones, no se
disfrazan de conexiones. Evitar que futuros vínculos dependan únicamente de reconocer
la apertura de un campo o el control Expandir. No uniformar todos los iconos ni crear
una pestaña adicional para una colección que ya tenga botón nativo.

### Continuidad comprobada sin cambios funcionales

La trazabilidad de la serie resuelve el origen de fabricación y conserva el retorno
al equipo. Los campos many2one de FEN y de la alerta ofrecen Enlace interno al
interactuar con el campo; se abrió la referencia actual sin seleccionar otro valor,
sin guardar ni confirmar documentos. Son enlaces nativos funcionales, pero menos
visibles que los botones Equipo / Orden de reparación de las revisiones.

Capturas: `serie-trazabilidad-fabricacion.png`, `fen-trn-apertura.png`,
`fen-equipo-apertura.png` y `calidad-orden-apertura.png` en la carpeta de evidencia.
QA realizada con el usuario administrador de STAGING, no certifica permisos de taller.

Recomendación concreta siguiente, todavía sin implementar: facilitar Abrir/Retomar
en las filas de FEN existentes y evaluar botones inteligentes para sus referencias
Equipo / Rendimiento / Terreno cuando existan. Deben abrir exactamente lo seleccionado,
sin sustituirlo por la última prueba ni crear otra ficha. Conservar edición de las
referencias en borrador y restricciones de la emitida. No modificar PDF.

Para Calidad → fabricación faltan alertas con MO/control de origen. No crear un
botón por la sola ausencia en esta muestra ni declarar la ruta comprobada; cerrar
ese caso con una muestra acordada o consulta focalizada del código instalado.

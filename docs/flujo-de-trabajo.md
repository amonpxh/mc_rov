# Cómo se sigue el trabajo entre los módulos

Actualizado: 2026-10-07, según el código de mc_rov 19.0.24.0.0 y los recorridos acordados.
Para taller, fabricación y responsables de aceptación.

Este documento describe el flujo disponible, no una nueva navegación ya implementada.
La propuesta de ayuda dentro de Odoo está en [Recorridos guiados](designs/flujo-guiado.md).
Los nombres de menús base y controles configurados deben comprobarse en la instalación.

## Cómo leer los recorridos

Este es un mapa de relaciones, no una secuencia obligatoria. Se puede comenzar en una
orden, una serie, una prueba o una incidencia y continuar según el trabajo. Consultar
un registro relacionado no crea otro. Una flecha expresa continuidad posible, no un
bloqueo ni una obligación. Los requisitos pertenecen a acciones concretas, como emitir FEN.

| Escenario | Recorrido orientativo | Rama condicional |
| --- | --- | --- |
| Modelo conocido sin cambios | Modelo/BoM vigente → fabricación → serie → configuración y aceptación | Controles configurados e incidencias, cuando existan. No modificar diseño por defecto. |
| Modelo nuevo | Definición del diseño/configuración → fabricación de validación → pruebas → ajustes → aceptación | Desarrollo y repetición según necesidad. El procedimiento de desarrollo y aprobación aún debe concretarse con taller/ingeniería. |
| Modelo conocido con variante o cambio | Definir la diferencia → configuración/BoM adecuada → fabricación → validación | Distinguir opción prevista, configuración particular y cambio de diseño. No toda diferencia requiere ECO. |
| Reparación/mantención de cliente | Orden → equipo/revisiones → intervención si corresponde → verificación → ficha/entrega | Repuestos y pruebas adicionales según intervención. Diagnóstico sin trabajos también es válido. |
| Reparación con actualización/mejora | Recorrido de reparación con una rama hacia ingeniería si corresponde | La mejora puede afectar solo a esa unidad. Una solicitud de mejora no necesita una alerta de Calidad si no hay incidencia. |
| Incidencia que requiere prevención | Origen → Calidad → procedimiento o diseño → futuras operaciones | Una sola incidencia puede justificar prevención; no esperar repeticiones ni asumir una causa por su frecuencia. |

## Relaciones para continuar el trabajo

Mapa acordado de destinos útiles, no certificación de que todos los accesos estén
instalados o comprobados en pantalla. La auditoría distingue esos estados en
[Recorridos guiados](designs/flujo-guiado.md), § 12–13.

| Desde | Destino y motivo |
| --- | --- |
| Fabricación | BoM utilizada; series producidas; controles de esa orden; alertas de esa orden; lecciones del modelo y cambios realmente vinculados/aplicables. |
| Equipo/serie | Reparaciones, revisiones y FEN de esa unidad; fabricaciones realmente relacionadas; alertas que afectan a la unidad. |
| Reparación | Equipo e historial de revisiones; alertas de la visita; ingeniería solo si una mejora/incidencia lo requiere. |
| REV/RND/TRN | Equipo y orden vinculada, cuando exista. Los botones Equipo / Orden de reparación ya están desplegados. |
| FEN | Equipo y RND/TRN explícitamente seleccionadas; conservar el documento emitido y su evidencia. |
| Alerta de calidad | Orden/control de origen, unidades afectadas y cambio de ingeniería cuando la resolución lo requiera. |
| Cambio de ingeniería | Producto/BoM, alertas que lo motivaron cuando existan y fabricación de validación cuando se haya vinculado. |
| Producto/modelo o BoM | Configuración/BoM adecuada, fabricaciones y cambios relacionados, con selección visible si hay varios. |

Un vínculo único puede ofrecer un botón como Equipo; una colección, un acceso con
conteo y lista filtrada; una referencia como BoM, un campo relacionado. Crear prueba,
alerta, fabricación o cambio es una acción diferente y explícita. No conectar todos
los módulos entre sí ni seleccionar silenciosamente el primer registro.

La BoM de una fabricación describe cómo se fabricó; la configuración actual de la
serie puede haber cambiado. Desde reparación, consultar el origen por Equipo →
Trazabilidad → fabricación de origen → BoM vinculada, sin presentar una supuesta «BoM del equipo»
única. La referencia a la BoM no garantiza una copia inmutable de su contenido
histórico. Reparar una unidad no crea por sí mismo otra fabricación. El botón nativo
de fabricaciones de la reparación abre las MO ligadas a sus referencias, no busca
la fabricación original por número de serie.

## Dónde interviene Calidad

Los controles nativos verifican operaciones configuradas; las alertas investigan y
documentan incidencias, corrección, alcance y prevención. RND/TRN son revisiones de
aceptación independientes: un No conforme en sus chequeos no equivale automáticamente
a un fallo de un control nativo ni genera por esa sola razón la misma alerta.

Hoy un control nativo fallido de un producto ROV registra una alerta vinculada.
Los trabajos de reparación pueden evaluarse mediante Candidatas a lección. Una
alerta puede enlazarse a un cambio de ingeniería; cerrada y con acción preventiva
puede aparecer como lección para futuras fabricaciones del modelo.

No toda avería de cliente es un defecto del modelo, ni toda alerta requiere cambiar
la BoM. La resolución puede ser corregir armado, configuración o procedimiento.
Un modelo nuevo o una mejora solicitada también pueden originar ingeniería sin alerta.

## Mapa rápido

| Necesito | Punto de entrada actual |
| --- | --- |
| Fabricar un ROV | Fabricación → Órdenes de fabricación |
| Ver lecciones de su modelo | Orden de fabricación → Lecciones del modelo, si existen y tengo acceso |
| Completar configuración | Inventario → Números de serie → equipo → Especificaciones |
| Probar rendimiento o terreno | Equipo → Pruebas → Nueva prueba de rendimiento / Nueva prueba en terreno |
| Retomar una prueba | Equipo → Pruebas → Editar/Abrir el registro existente |
| Preparar FEN | Equipo → Imprimir ficha → seleccionar RND/TRN |
| Retomar una FEN | Equipo → Fichas → Retomar / Abrir la ficha |
| Recibir y reparar | Reparaciones → Órdenes |
| Completar una revisión de la visita | Orden → Revisiones → Editar/Abrir |
| Imprimir ficha reparada | Orden → Revisiones → Imprimir ficha → verificar revisión seleccionada |
| Evaluar aprendizaje de reparaciones | Reparaciones → Candidatas a lección |

## 1. Equipo nuevo: fabricación, configuración y aceptación

### Fabricación

La orden de fabricación registra el modelo, materiales y trabajo. Las lecciones cerradas
con acción preventiva del modelo aparecen en Lecciones del modelo, si hay alguna.
Una MO puede producir varias series; cada serie identifica un equipo y su historial.
No asumir que todas las series se crean al terminar: depende de la operativa nativa.

Los controles de calidad dependen de su configuración. **No hay una batería de armado
específica de mc_rov que este documento deba exigir:** la propuesta anterior se descartó.
Si existe un control configurado para un producto ROV y falla, la extensión registra una
alerta o el reintento en la alerta abierta. Eso no equivale a tener controles de armado
ya definidos ni a una validación completa del equipo.

### Configuración del equipo

Abrir su número de serie y completar Especificaciones: estructura, motores, umbilical,
periféricos, tarjetas, software y ajustes. El aviso indica qué datos faltan y permite
guardar lo que ya se conoce sin inventar los demás.

No hay que vaciar campos de software ni copiarlos dos veces: RND puede precargarlos
según la ficha y actualizarla al confirmarse conforme a las reglas del modelo.
Los equipos anteriores al sistema pueden configurarse sin inventar una MO o prueba.

### Pruebas RND y TRN

Desde Pruebas, cada botón Nueva prueba crea un intento independiente. Para continuar
uno abierto, usar Editar/Abrir en su historial, en lugar de crear otra prueba.

- **RND:** validación de rendimiento, condiciones, mediciones, software y chequeos.
- **TRN:** validación en terreno, lugar, profundidad, corriente, duración y pruebas aplicables.

Ambas mantienen sus registros e intentos. Confirmar exige completar los datos requeridos;
el resultado puede ser aprobado, aprobado con observaciones o rechazado.
Confirmada no significa aprobada. Las temperaturas son internas y no se imprimen.

### Ficha de equipo nuevo (FEN)

Imprimir ficha abre el asistente centrado en la serie. Propone la candidata más reciente
por fecha/id de cada tipo: borrador o confirmada aceptada, del mismo equipo y sin orden
de reparación. La selección permanece visible y puede cambiarse.

Una revisión antigua puede llamarse REV aunque su tipo real sea rendimiento o terreno.
Se filtra por su tipo y relación, no por el texto del número. Las confirmadas rechazadas
no son elegibles; continúan en el historial del equipo.

- **Guardar borrador:** crea una ficha persistente con las referencias elegidas.
- **Vista previa:** genera PDF sin emitir, incluso si faltan pruebas o están en borrador.
- **Emitir ficha:** requiere ambas pruebas confirmadas y aceptadas; almacena el PDF final.
- **Imprimir ficha emitida:** descarga el PDF almacenado; nuevas revisiones no lo reemplazan.

Para retomar una FEN existente, abrirla en su historial. Volver a preparar y guardar
una ficha desde el asistente crea otro documento, no edita automáticamente el anterior.
FEN tiene correlativo propio asignado al crear, incluso en borrador; no es el número del ROV.

### Entrega

La emisión FEN respalda la aceptación documental. La entrega física/comercial pertenece
al flujo correspondiente de Inventario/Ventas/Alquiler. No se afirma que mc_rov bloquee
esas operaciones por falta de pruebas: ese control no está implementado en el código auditado.

## 2. Equipo que vuelve al taller

### Recepción y entrada

Crear la orden, seleccionar equipo/serie y registrar intervención, síntomas, sospechas
y accesorios recibidos. Al salir de borrador, un ROV obtiene su primera revisión de
reparación si la visita no tiene una. No es necesario crearla otra vez.

### Diagnóstico

En Revisiones, abrir el registro de esta visita. Sellos, Pruebas y Hallazgos registran
lo que se comprobó. Los chequeos usan **Conforme / No conforme / No aplica**;
una respuesta vacía es **Pendiente**, no No aplica.
El historial completo del equipo permite comparar otras visitas sin mezclarlas con esta.

### Trabajos y verificación

En Trabajos realizados registrar lo intervenido; en Repuestos registrar piezas usadas.
Hallazgos y trabajos son registros distintos: el vínculo de origen permite relacionarlos.
Electrónica y Software / Configuración son componentes separados del catálogo.

Si se necesita otro pase, Nueva revisión crea una revisión de la visita. Indicar su
motivo, por ejemplo re-test tras reparación o comparación de umbilical. El sistema
no decide automáticamente que toda visita necesita ese pase.

### Ficha y cierre

Imprimir ficha propone la revisión de reparación más reciente de esta orden.
Verificar que corresponda al documento que se quiere entregar: reciente no significa
necesariamente re-test final aprobado. El asistente permite elegir otra revisión.

Para cerrar se valida tipo de intervención, origen de cada trabajo y al menos un
repuesto cuando alguna acción lo consume. Si falta fecha de entrega real, se sella
con la fecha de cierre. Una revisión sin confirmar genera una señal de pendiente,
pero no bloquea el cierre. Un diagnóstico sin trabajos puede cerrarse.
No confundir cerrar la orden con registrar todas las operaciones comerciales de entrega.

## 3. Aprendizaje y cambios de modelo

La entrada **Candidatas a lección** permite seleccionar trabajos, escribir una lección
del modelo o descartarlos con motivo. La lección vive en una alerta de calidad y se
relaciona con los trabajos. No hay que buscar un botón retirado en cada línea de trabajo.

Las alertas cerradas con acción preventiva pueden aparecer como lecciones en futuras
órdenes del mismo modelo. Corregir un equipo y prevenir una repetición son decisiones
distintas; cerrar una alerta sin acción preventiva no la convierte en lección.

Si corresponde modificar el diseño/lista de materiales, PLM registra el cambio.
Tipos de ECO, aprobaciones y uso efectivo de PLM se validan con la operativa de la empresa;
este mapa no afirma que esos controles estén configurados ni que Odoo impida editar a mano.

## 4. Qué falta facilitar

Los enlaces y acciones existen en gran parte, pero el usuario todavía necesita ubicar
módulos y pestañas. Antes de agregar botones, comprobar dónde la navegación nativa basta
y dónde falta una guía: retomar revisión, volver a orden/equipo, pasar de MO a serie y
llegar al apartado donde se resuelve cada tarea.

La mejora se diseña en [Recorridos guiados](designs/flujo-guiado.md). No cambia los PDF,
no introduce estados paralelos y no impone nuevos bloqueos de cierre o entrega.

# Centro de trabajo ROV

Fecha: 2026-10-08. Estado: propuesta y maqueta local; no implementado en Odoo.

## Propósito

Encontrar dónde comenzar y retomar trabajo sin memorizar módulos. El centro abre
registros y listas existentes; no crea otro proceso, otra fuente de estados ni una
lista obligatoria de pasos. Sustituye la necesidad de buscar menús, no las pestañas
de una orden. La guía lateral descartada no se recupera.

Entrada propuesta: menú ROV → Centro de trabajo. No reemplazar el inicio general
de Odoo. Primera versión compartida: no llamarla «Mis tareas», porque usuario que
registra y técnico responsable no son necesariamente la misma persona.

## Contenido mínimo propuesto

| Área | Comenzar | Retomar / consultar |
| --- | --- | --- |
| Reparaciones | Crear orden de reparación/mantención | Órdenes abiertas y revisiones de reparación en borrador |
| Fabricación / aceptación | Crear fabricación; elegir equipo para aceptación | Fabricaciones abiertas, RND/TRN en borrador y FEN en borrador |
| Equipos | Buscar número de serie | Configuración, historial y documentos del equipo elegido |
| Calidad | Registrar incidencia | Alertas abiertas; acceso separado a Candidatas a lección |
| Diseño / BoM | Nuevo producto/modelo, nueva BoM o nuevo cambio de ingeniería, como acciones distintas | Consultar modelos/BoM existentes y retomar cambios de ingeniería |

Crear una fabricación abre el formulario nativo: no modifica automáticamente BoM
ni crea ECO. Aceptación comienza eligiendo un equipo existente; no fabrica ni
emite una FEN silenciosamente. Retomar FEN abre el documento elegido, no vuelve
al asistente que crearía otro. Retomar una prueba abre el intento elegido.

Diseño/BoM e ingeniería tienen una entrada por necesidad propia, disponible cuando
se necesita, sin badge de pendiente. Un «diseño nuevo» no implica inventar otro
modelo de datos: diferenciar producto/modelo, su BoM y la gestión de cambios en PLM.
Los destinos nativos concretos y el procedimiento para modificar una BoM se
contrastarán antes de implementar. No prometer un editor CAD dentro de Odoo.
Los controles configurados se encuentran en su fabricación;
no asumir una batería universal ni exigir controles a órdenes que no los tienen.

## Conteos y límites

| Etiqueta | Fuente y criterio propuesto |
| --- | --- |
| Órdenes abiertas | repair.order en confirmed / under_repair; borradores aparte |
| Fabricaciones abiertas | mrp.production en confirmed / progress / to_close; borradores aparte |
| Pruebas en borrador | mc.rov.revision.estado=borrador, separadas por tipo real |
| Fichas en borrador | mc.rov.ficha.equipo.nuevo.estado=borrador |
| Alertas abiertas | quality.alert cuya etapa no esté marcada como cerrada |

Los dominios nativos y permisos deberán verificarse antes de implementar; los
conteos y sus listas usarán el mismo dominio, compañía y acceso del usuario, sin
sudo. No incluir registros ajenos a ROV en los conteos de este centro. Ocultar
acciones no autorizadas; diferenciar falta de acceso de cero registros.

Un borrador puede estar pausado o ser histórico: el conteo indica estado, no
urgencia ni incumplimiento. No sumar todos los conteos como «tareas pendientes»:
una orden y su revisión pueden representar el mismo trabajo. No afirmar que faltan
repuestos, que alguien revisó registros o que una unidad espera aceptación sin
datos que lo demuestren. No inferir que toda serie sin FEN debe tener una.

Listas con referencia, equipo/modelo y estado; acceso explícito al registro exacto.
Permitir buscar y ver todos. El centro no seleccionará «el último» silenciosamente.
El trabajo continúa en formularios nativos y sus conexiones ya implementadas.

## Maqueta de navegación

Prototipo desechable fuera del módulo: ../.tmp/centro-trabajo-rov-prototype.
Datos ficticios, sin consultas ni escrituras en Odoo. Botones abren simulaciones.

- A — Por proceso: cuatro entradas y lista de la sección seleccionada.
- B — Retomar primero: lista de registros con filtros; crear en un área secundaria.
- C — Necesidad + registros (actualizada): seis entradas que seleccionan el área;
  debajo aparecen los registros existentes y acciones explícitas para crear.
  Fabricación y aceptación se separan. Calidad incluye consulta de controles,
  alertas y Candidatas a lección. Diseño/BoM incluye modelos, BoM y cambios.

El usuario aprobó explorar la combinación de nombres por necesidad de C con la
selección de área de A. Las tarjetas no crean registros al pulsarlas. Nueva orden,
nueva fabricación y demás creaciones son botones separados; Abrir/Retomar elige
un registro existente. A/B se conservan solo como comparaciones anteriores.

Nombres aprobados el 2026-10-08: «Aceptar un equipo nuevo» y «Trabajar en diseño /
BoM». Descripción de esta última solicitada por el usuario:
«Modelos, BoM (lista de materiales) y cambios de ingeniería». «Preparar aceptación»
expresa preparación pero omite qué se acepta; «Modelos y cambios» limita la promesa
de diseño, pero es menos explícito sobre BoM y pierde el verbo de necesidad.
La tarjeta selecciona un área; nunca aprueba, emite o modifica diseño con un clic.

Refinamiento local de C: tarjetas compactas; filtros locales por tipo de registro
(órdenes/revisiones, equipos/rendimiento/terreno/fichas, alertas/controles/lecciones,
modelos/BoM/cambios); búsqueda explícita dentro de la sección; acción de creación
según tipo elegido y «Ver todas…» con destino explícito. Consultar equipo incorpora
modelo opcional, serie y estado operativo; mantiene filtros al abrir/cerrar el
destino simulado o cambiar de área durante la sesión de maqueta. No se certifica
persistencia de filtros en Odoo ni tras recargar: falta implementación.

Conteos de ejemplo por tipo, sin total de tareas. Catálogos/equipos se consultan
sin imponer estado de pendiente; documentos y operaciones tienen vista inicial
en curso/borradores y opción Todos los estados. FEN emitida se consulta desde
Todos los estados. Estados vacíos no crean registros por sí solos. La barra de
comparación A/B/C sigue siendo herramienta temporal, no parte del producto final.

Pasada de estilo solicitada el 2026-10-08: jerarquía de título/área/filtros,
tarjetas con acento lateral para la seleccionada, pestañas subrayadas con conteos
discretos, bordes/radios/espacios consistentes y creación separada a la derecha.
Paleta cercana a Odoo; rótulo de maqueta neutro para no parecer una alerta operativa.
Foco visible y disposición adaptable a pantallas estrechas. Los nombres, destinos,
filtros y lógica de la maqueta se conservan; no cambia el módulo Odoo.

Auditoría de destinos instalada completada el 2026-10-08 con rollback confirmado:
`../.tmp/center-work-audit/installed.json`. Acciones elegidas y diferencias respecto
a la maqueta documentadas en el plan de implementación. FEN carece de acción de
lista general; ECO se filtra por state y no por un supuesto done de etapa. Las
acciones generales evitan dependencias de active_id de otra operación. Menús y
ACL deben evaluarse para el usuario real; la sonda administrativa no certifica
permisos de cada perfil.

No se afirma cubrir todas las necesidades del ERP: esta propuesta cubre los
recorridos técnicos ROV acordados. Compras, ventas, alquileres y logística no se
agregan sin definir su alcance. Pendiente validar con usuario claridad y densidad
de las seis entradas, especialmente diseño/BoM y Calidad.

## Fuera de esta fase

Indicadores de desempeño, prioridades automáticas, asignaciones personales,
notificaciones, nuevas obligaciones, cambios de PDFs y despliegues. Muestras reales
de varias series, FEN emitida y controles configurados siguen pendientes para la
puesta en marcha; no bloquean esta exploración visual.

Composición C, términos y estilo aprobados el 2026-10-08. Piloto activado y
aprobado por el usuario en STAGING: 16 contratos backend, suite completa de 378
pruebas y 10 contratos HOOT verificados antes del cierre. Filtros conservados al
volver del formulario; modelos históricos visibles y alcance de compañía probado.
Los estados operativos son Operativo, En mantención y En reparación.

## Cierre visual aprobado

- Aplicación y título: **Centro de trabajo**.
- Icono: propuesta de conexiones con círculos amarillo, coral, turquesa y morado;
  versión anterior morada elegida después de comparar la alternativa azul.
  Colores base tomados de la referencia Odoo, cruces por mezcla multiplicativa.
  PNG 256 px y fuente SVG conservados en `static/src/img/work_center_icon.*`.
- Sin logo MC dentro de la pantalla: para uso interno se prioriza el espacio de
  trabajo. La maqueta de branding no se incorpora al módulo ni al despliegue.
- Tarjetas con contorno gris cerrado, marca morada de selección y foco visible.
- Raíz limitada a la altura del área de Odoo con scroll propio: el pie y los
  controles de tabla son accesibles también en pantalla estrecha.

Integración y despliegue autorizados por el usuario. La última pasada local de
formato/lint reorganizó helpers sin alterar los contratos; suite de cierre del
árbol final aprobada 378/378 y servicio activo. Icono/nombre verificados en el
lanzador nativo. Estado de PR y producción en `../pendientes.md`.

## Responsables e icono — ajuste aprobado el 2026-10-09

Las listas muestran la persona ya registrada, sin asignar tareas ni inferirla del
autor o último editor. REV/RND/TRN usan «Técnico responsable» y la ayuda «Persona
registrada como responsable de realizar la prueba.»; FEN, reparación, fabricación,
controles/alertas de Calidad y cambios de ingeniería usan «Responsable».
Los campos nativos fueron auditados en STAGING. Los nombres de empleados se leen
mediante `hr.employee.public`, conservando permisos y reglas de acceso.
Sin persona: «Sin responsable»; nombre no accesible: «Sin acceso al nombre».
Modelos, BoM y equipos no incorporan columna; el responsable logístico del producto
no representa al responsable del diseño. Actividades programadas quedan para después.

El icono conserva posiciones, ángulos y círculo blanco; amplía los brazos de 32 a
40 y ajusta la escala para ocupar 126 × 126 px en el render de referencia, igual
que Contactos y Ventas. No incorpora desplazamiento ni rotación de figuras.

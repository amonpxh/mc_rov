# Trabajo pendiente

> Actualizar esta sección al cerrar cada sesión de trabajo.

## Estado al 2026-08-14

La **revisión técnica** está implementada (`19.0.12.0.0`): seis modelos, los catálogos de
chequeos y hallazgos, la inspección de sellos, y **una** revisión por visita que se abre sola
al confirmar la orden. Diseño en
[`designs/revision-tecnica.md`](designs/revision-tecnica.md).

`19.0.12.0.0` salió de probar el módulo en pantalla, que es de donde salió todo lo que
importaba: el par recepción/entrega se retiró, la pestaña de pruebas se rehízo por secciones
como la hoja de papel, y el catálogo salió del alcance de quien llena la ficha. Las
correcciones de alcance quedan registradas en § 1.3 y § 1.4 del diseño.

**Pendiente de validar en producción** (el deploy es lo único que lo puede confirmar):

- Que `open_form_view` rinda en el one2many embebido de Odoo 19. Si no, el reemplazo es
  quitar el `readonly` del campo y poner `create="0" delete="0"` en la lista.
- Que esconder `tag_ids` con `position="attributes"` no choque con el arch base — el nombre
  del campo se dedujo de la pantalla, no se leyó del código de `repair`.

Lo que sigue del plan original, en orden:

- [ ] **Reporte PDF de las dos fichas** (`19.0.9.0.0` del plan, ahora la siguiente versión
  grande). Ni la ficha de fabricación ni la revisión técnica se pueden imprimir hoy; el
  único documento imprimible de una orden es el presupuesto por defecto de Odoo.

  **La revisión existe, entre otras cosas, para entregársela al cliente**, así que esto no
  es un extra. Obliga a decidir campo por campo qué es interno y qué va impreso — ver
  [`designs/revision-tecnica.md`](designs/revision-tecnica.md) § 12.1.

- [ ] **Fotos de los hallazgos**, con `fields.Image(max_width=1920, max_height=1920)` y no
  `fields.Binary`. Decidido dejarlo para el final. El disco no es problema: 50 GB libres y
  los adjuntos van a disco, no a la base.

- [ ] **Vista de búsqueda de `repair.order`** — filtrar por tipo de intervención, agrupar
  por causa raíz, y `mc_total_horas` al pie de la columna con `sum`.

  El dato que faltaba ya se averiguó: la vista base se llama
  **`repair.view_repair_order_form_filter`**, su grupo de "agrupar por" no tiene nombre pero
  el último filtro adentro sí (`group_by_repair_properties`), y **el schema de Odoo 19
  rechaza `expand` y `string` en el elemento `group`** — eso rompió el módulo una vez.

- [ ] **Phase -1 del pipeline roadmap — Foundation handoff** — prerequisito bloqueante para iniciar el pipeline. Checklist completo en `rov-pipeline-roadmap.md` Phase -1. Duración estimada: 1 semana.

- [ ] **Separar el workspace del runner de CI del addons de producción.** Hoy son el mismo directorio: `/opt/odoo/custom-addons/mc_rov`. Descubierto el 2026-08-07 al desplegar `19.0.5.0.0`.

  **El deploy en sí ya no es el problema**: el usuario `odoo` tiene deploy key y hace `fetch` por su cuenta. Lo único que fallaba era que el runbook decía `git pull` a secas, que corre como root — corregido en [`runbooks/deploy.md`](runbooks/deploy.md).

  Lo que queda es el directorio compartido: **un job de CI puede cambiar lo que Odoo está sirviendo**, porque el checkout aterriza en el addons path de producción. Desplegar no es lo único que mueve ese código.

  Arreglo: mover el workspace del runner fuera de `/opt/odoo/custom-addons/mc_rov`. No urge —el deploy funciona y es deliberado— pero es una fuente de sorpresas que nadie va a relacionar con CI cuando ocurra.

- [ ] **Carga de productos ROV** — el árbol de categorías ya está en producción (164 categorías), pero todavía no hay productos ROV cargados. Al cargarlos:

  1. **La categoría dejó de ser un dato descriptivo y pasó a ser funcional.** Desde `19.0.2.0.0` el campo `es_un_rov` se deriva de ella: un vehículo cargado fuera de la rama `ROV - Vehiculos` (id `968` en `odoo_prod`) no tendrá ficha técnica ni pestañas de mantención, y nadie podrá encenderlas a mano.
  2. `ROV-MC` para vehículos de marca propia, `ROV-XX` para los de otras marcas. Ambas ramas encienden la marca.
  3. **El síntoma de equivocarse no apunta a la causa.** El técnico va a reportar "no me aparecen las pestañas", no "la categoría está mal". Revisar la categoría del producto antes que el módulo.
  4. Los equipos de clientes entran en consignación: la categoría dice **qué es** el equipo, la propiedad se maneja aparte. Ver [`INVENTARIO.md`](../INVENTARIO.md) § Equipos de clientes.
  5. **Llenar `mc_propietario_id` al cargar cada número de serie.** Desde `19.0.5.0.0` de ahí sale el estado comercial: un equipo vendido que quede a nombre de la empresa va a aparecer como "Disponible" y va a ensuciar la lista de flota. Los que son de clientes se cargan a nombre del cliente; los de flota se dejan como vienen, ya que el valor por defecto es la propia empresa.
  6. **Llenar también `mc_fecha_puesta_servicio`** en los equipos que ya están en terreno, o el reloj de mantención no arranca y no aparecerán nunca en la lista de vencidos.
  7. **Desde `19.0.6.0.0` hay catorce campos más que llenar por equipo**, no dos. Toda la pestaña *Especificaciones* pasó a ser obligatoria para los ROV: chasis, modelo / N° / posición de motores, ambos pesos, sensor de presión, ambas tarjetas de comunicación, controlador de vuelo y su versión, ArduSub, software de superficie y su versión, y cantidad de luces.

     **La obligatoriedad vive en la vista, no en el modelo**, así que una **importación entra igual con los campos vacíos** — eso es deliberado, porque un `required` de modelo rompería la creación de series desde la orden de fabricación. Lo que encuentra a las series incompletas es el campo `mc_ficha_completa` y el filtro **«Ficha incompleta»** en la lista de números de serie. Después de cualquier carga masiva, revisar ese filtro.

     Cuidado con los numéricos: en Odoo un `Integer` o un `Float` nunca queda vacío, se lee como 0, así que N° de motores, ambos pesos y cantidad de luces pueden entrar en cero sin que nada chiste. `mc_ficha_completa` los exige `> 0` justamente por eso.

     Y **ya no hay opción «Desconocido»**: se probó en `19.0.6.0.0` y se retiró en `19.0.7.0.0`, porque la decisión es obligar a averiguar las especificaciones reales del equipo. Para los equipos anteriores a Odoo eso significa que hay que ir a levantar el dato o poner un valor supuesto — y un valor supuesto es indistinguible de uno verificado, que es el precio conocido de esa decisión.

  **Residuo a limpiar antes de cargar datos reales:** quedan 2 números de serie de prueba con `es_un_rov = TRUE` cuya cadena producto → categoría está rota; por eso la migración `19.0.2.0.0` reportó 0 filas recalculadas y no los tocó. Se apagarán solos la primera vez que algo los escriba. Conviene borrarlos para no confundirlos con equipos reales.

- [ ] **Grupos de seguridad**: los accesos actuales son sin grupo. Implementar cuando haya múltiples usuarios. Diseño acordado:

  **Dos grupos jerárquicos** (`Coordinador ROV` hereda `Técnico ROV` vía `implied_ids`):

  | Grupo | `implied_ids` (grupos Odoo arrastrados) | Acceso mc_rov |
  |-------|----------------------------------------|---------------|
  | `Técnico ROV` | `repair.group_repair_user`, `stock.group_stock_user` | CRUD en `linea.falla`; lectura en `componente`/`subtipo`/`accion`; edición de ficha técnica y campos mc_rov en `repair.order` y `stock.lot` |
  | `Coordinador ROV` | `repair.group_repair_manager`, `stock.group_stock_manager`, `purchase.group_purchase_user`, `sale.group_sale_user`, `account.group_account_invoice` | Todo lo anterior + CRUD en `componente`/`subtipo`/`accion` |

  **Implementación involucra:**
  1. `security/mc_rov_groups.xml` — definir los dos grupos con `implied_ids`
  2. `ir.model.access.csv` — reemplazar líneas sin grupo por reglas por grupo
  3. `views/` — agregar `groups=` en campos que solo el Coordinador debe editar (ej. `mc_estado_comercial`)
  4. Registrar `mc_rov_groups.xml` en `__manifest__.py` bajo `data`

  **Para asignar grupos a usuarios:** `Ajustes → Usuarios → [usuario]` (sin tocar código). Cambiar qué puede hacer un grupo requiere modificar el módulo.

- [ ] **Validación de línea de producto en cierre de orden**: hoy una orden se puede cerrar con líneas de falla de tipo "cambio" sin haber registrado el repuesto como línea de producto.

  **Desde `19.0.5.2.0` ya hay dónde ponerla**: el override de `write` en `repair_order.py` valida la transición a `done` antes del `super()` para exigir el tipo de intervención. La misma validación cubre este caso sin infraestructura nueva. Cuando eso pasa se pierde el vínculo con el lote y se corta el análisis de fallas. Diseño acordado:

  1. `mc.rov.accion` — agregar booleano `consume_repuesto`. Marcarlo en "Cambio completo" y "Cambio de componente"; el resto de las acciones (limpieza, calibración, configuración, soldadura) queda en `False`.
  2. `repair.order` — constraint o `write` override: si alguna línea de `linea_falla_ids` tiene `accion_id.consume_repuesto = True`, la orden no puede pasar a `done` sin al menos una línea de producto.
  3. `data/mc_rov_data.xml` — setear el booleano en las 10 acciones existentes.

  **No hardcodear a los dos nombres de acción.** El catálogo es configurable desde el menú: si mañana agregan "Reemplazo de sello", tienen que poder marcar la casilla sin tocar código.

- [ ] **Pipeline integration touchpoints** (Phase 1 del pipeline — requiere Phase -1 completada primero): agregar `controllers/api.py`, usuario `pipeline@marine-connection` con API key, y grupo `Pipeline API (Read-Only)`. Checklist en `rov-pipeline-roadmap.md` Phase 1 "Odoo access layer". Contrato en [`integrations/pipeline.md`](integrations/pipeline.md).

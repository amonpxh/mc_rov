# Trabajo pendiente

> Actualizar esta sección al cerrar cada sesión de trabajo.

- [ ] **Phase -1 del pipeline roadmap — Foundation handoff** — prerequisito bloqueante para iniciar el pipeline. Checklist completo en `rov-pipeline-roadmap.md` Phase -1. Duración estimada: 1 semana.

- [ ] **Separar el workspace del runner de CI del addons de producción.** Hoy son el mismo directorio: `/opt/odoo/custom-addons/mc_rov`. Descubierto el 2026-08-07 al desplegar `19.0.5.0.0`.

  1. **`git pull` como root no funciona y nunca funcionó** — el remoto es SSH y root no tiene deploy key. El runbook documentaba ese comando; ya está corregido en [`runbooks/deploy.md`](runbooks/deploy.md) con el workaround real (`merge --ff-only origin/main`, que es local porque el runner ya dejó los refs actualizados).
  2. **El código llega a producción por efecto secundario de CI**, no por una acción deliberada de desplegar. Un job de CI puede cambiar lo que Odoo está sirviendo.
  3. Arreglo: mover el workspace del runner fuera del addons path, y darle al deploy una credencial propia de solo lectura. Recién ahí el runbook puede volver a decir `git pull`.

  **Mientras tanto**, verificar siempre `git log --oneline -1` y la versión del manifiesto antes de correr el `-u mc_rov`. Desplegar la migración equivocada sobre `odoo_prod` no se deshace con un `git checkout`.

- [ ] **Carga de productos ROV** — el árbol de categorías ya está en producción (164 categorías), pero todavía no hay productos ROV cargados. Al cargarlos:

  1. **La categoría dejó de ser un dato descriptivo y pasó a ser funcional.** Desde `19.0.2.0.0` el campo `es_un_rov` se deriva de ella: un vehículo cargado fuera de la rama `ROV - Vehiculos` (id `968` en `odoo_prod`) no tendrá ficha técnica ni pestañas de mantención, y nadie podrá encenderlas a mano.
  2. `ROV-MC` para vehículos de marca propia, `ROV-XX` para los de otras marcas. Ambas ramas encienden la marca.
  3. **El síntoma de equivocarse no apunta a la causa.** El técnico va a reportar "no me aparecen las pestañas", no "la categoría está mal". Revisar la categoría del producto antes que el módulo.
  4. Los equipos de clientes entran en consignación: la categoría dice **qué es** el equipo, la propiedad se maneja aparte. Ver [`INVENTARIO.md`](../INVENTARIO.md) § Equipos de clientes.
  5. **Llenar `mc_propietario_id` al cargar cada número de serie.** Desde `19.0.5.0.0` de ahí sale el estado comercial: un equipo vendido que quede a nombre de la empresa va a aparecer como "Disponible" y va a ensuciar la lista de flota. Los que son de clientes se cargan a nombre del cliente; los de flota se dejan como vienen, ya que el valor por defecto es la propia empresa.
  6. **Llenar también `mc_fecha_puesta_servicio`** en los equipos que ya están en terreno, o el reloj de mantención no arranca y no aparecerán nunca en la lista de vencidos.

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

- [ ] **Validación de línea de producto en cierre de orden**: hoy una orden se puede cerrar con líneas de falla de tipo "cambio" sin haber registrado el repuesto como línea de producto. Cuando eso pasa se pierde el vínculo con el lote y se corta el análisis de fallas. Diseño acordado:

  1. `mc.rov.accion` — agregar booleano `consume_repuesto`. Marcarlo en "Cambio completo" y "Cambio de componente"; el resto de las acciones (limpieza, calibración, configuración, soldadura) queda en `False`.
  2. `repair.order` — constraint o `write` override: si alguna línea de `linea_falla_ids` tiene `accion_id.consume_repuesto = True`, la orden no puede pasar a `done` sin al menos una línea de producto.
  3. `data/mc_rov_data.xml` — setear el booleano en las 10 acciones existentes.

  **No hardcodear a los dos nombres de acción.** El catálogo es configurable desde el menú: si mañana agregan "Reemplazo de sello", tienen que poder marcar la casilla sin tocar código.

- [ ] **Pipeline integration touchpoints** (Phase 1 del pipeline — requiere Phase -1 completada primero): agregar `controllers/api.py`, usuario `pipeline@marine-connection` con API key, y grupo `Pipeline API (Read-Only)`. Checklist en `rov-pipeline-roadmap.md` Phase 1 "Odoo access layer". Contrato en [`integrations/pipeline.md`](integrations/pipeline.md).

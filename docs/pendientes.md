# Trabajo pendiente

> Actualizar esta sección al cerrar cada sesión de trabajo.

- [ ] **Phase -1 del pipeline roadmap — Foundation handoff** — prerequisito bloqueante para iniciar el pipeline. Checklist completo en `rov-pipeline-roadmap.md` Phase -1. Duración estimada: 1 semana.

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

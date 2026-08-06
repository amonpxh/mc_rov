# mc_rov — Módulo Odoo para Gestión de ROVs (Marine Connection)

## Descripción

Módulo Odoo 19 que extiende `repair` para gestionar reparaciones y mantenciones de equipos ROV (Remotely Operated Vehicles). Desarrollado para Marine Connection.

## Convenciones de código

Los comentarios deben explicar el **por qué**, no repetir lo que el código ya dice. Se espera:
- Docstring de clase en cada modelo explicando su rol en el dominio
- Comentario en campos cuyo propósito no sea obvio por el nombre
- Comentario en métodos `compute` y `onchange` explicando la lógica de negocio
- En herencias, indicar brevemente qué se extiende y la razón

## Flujo de trabajo con git

Estrategia: **GitHub Flow simplificado**. Estado actual: desarrollador único con despliegue directo a producción — bus factor 1, que **Phase -1 del pipeline roadmap está diseñada para resolver** (ver sección Pendiente). Mantener disciplina de PR desde ya para que el flujo esté en su lugar cuando se sume un colega.

```
main         ──●──────────────────────●──→  producción (Odoo server)
               │                     ↑
feature/X      └──●──●──●────────────┘
fix/Y                └──●──●─────────┘
```

- `main` = siempre estable y desplegable. No commitear directamente salvo hotfixes triviales.
- `develop` = rama de integración para agrupar cambios antes de subir a main.
- Toda funcionalidad nueva parte desde `main` (o `develop`) y hace merge al terminar.
- Tras el merge a `main`: `git push origin main` → actualizar módulo en el servidor Odoo.

### Nomenclatura de ramas

| Tipo | Formato | Ejemplo |
|------|---------|---------|
| Nueva función | `feature/<nombre>` | `feature/reporte-pdf-reparacion` |
| Corrección | `fix/<nombre>` | `fix/ultima-mantencion-fecha-real` |
| Refactor | `refactor/<nombre>` | `refactor/grupos-seguridad` |

### Versionado del módulo

El número de versión en `__manifest__.py` sigue el formato `19.0.X.Y.Z`:

| Segmento | Cuándo subirlo |
|----------|---------------|
| `19.0` | Nunca — fijo a la versión de Odoo |
| `X` | Cambio que rompe datos existentes (migración necesaria) |
| `Y` | Nueva funcionalidad compatible hacia atrás |
| `Z` | Bug fix o cambio menor |

### Formato de commits (Conventional Commits)

`tipo: descripción corta en español`

| Tipo | Cuándo |
|------|--------|
| `feat:` | Nueva funcionalidad |
| `fix:` | Corrección de bug |
| `docs:` | Solo documentación |
| `refactor:` | Reestructuración sin cambio de comportamiento |
| `style:` | Formato / CSS |
| `data:` | Datos maestros XML |
| `chore:` | Mantenimiento (dependencias, config) |

### Ciclo de vida de una tarea

```bash
git checkout main && git pull
git checkout -b feature/mi-funcion
# desarrollar, commitear con el formato de arriba
git checkout main
git merge feature/mi-funcion
git push origin main
git branch -d feature/mi-funcion
```

## Estado actual

> Actualizar esta sección al cerrar cada sesión de trabajo.

### Pendiente

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

- [ ] **Validación de línea de producto en cierre de orden**: hoy una orden se puede cerrar con líneas de falla de tipo "cambio" sin haber registrado el repuesto como línea de producto. Cuando eso pasa se pierde el vínculo con el lote y se corta el análisis de fallas (ver [`docs/inventario.md`](docs/inventario.md) § "El puente es la orden de reparación"). Diseño acordado:

  1. `mc.rov.accion` — agregar booleano `consume_repuesto`. Marcarlo en "Cambio completo" y "Cambio de componente"; el resto de las acciones (limpieza, calibración, configuración, soldadura) queda en `False`.
  2. `repair.order` — constraint o `write` override: si alguna línea de `linea_falla_ids` tiene `accion_id.consume_repuesto = True`, la orden no puede pasar a `done` sin al menos una línea de producto.
  3. `data/mc_rov_data.xml` — setear el booleano en las 10 acciones existentes.

  **No hardcodear a los dos nombres de acción.** El catálogo es configurable desde el menú: si mañana agregan "Reemplazo de sello", tienen que poder marcar la casilla sin tocar código.

- [ ] **Pipeline integration touchpoints** (Phase 1 del pipeline — requiere Phase -1 completada primero): agregar `controllers/api.py`, usuario `pipeline@marine-connection` con API key, y grupo `Pipeline API (Read-Only)`. Checklist en `rov-pipeline-roadmap.md` Phase 1 "Odoo access layer". Contrato en [`docs/integrations/pipeline.md`](docs/integrations/pipeline.md).

## Notas técnicas

- `ultima_mantencion` en `stock.lot` usa `fecha_entrega_real` de la última orden `done`, ingresada por el técnico al cerrar la orden.
- El dominio `[('componente_id', '=', componente_id)]` en `subtipo_id` dentro del one2many editable funciona correctamente desde Odoo 17+.
- Los campos de ficha técnica en `stock.lot` reemplazaron los `x_studio_*` de Studio. Los campos Studio siguen en la BD como columnas huérfanas — se pueden eliminar desde Studio o vía SQL cuando se confirme que no hacen falta.
- **Patrón de migración**: el ORM de Odoo crea las columnas nuevas **antes** de ejecutar el script `post-migrate.py`. Por eso las migraciones de renombrado deben usar `UPDATE SET nuevo = viejo` + `DROP COLUMN viejo`, no `RENAME COLUMN` (que falla porque la columna destino ya existe).
- **Operación en producción:** ver [`docs/runbooks/deploy.md`](docs/runbooks/deploy.md) — incluye comandos de deploy, verificación, y rollback.
- **Correr tests:** ver [`docs/runbooks/testing.md`](docs/runbooks/testing.md) — incluye sintaxis `--test-tags` y gotchas de Odoo 17+.
- **Contexto de inventario:** el diseño de categorías, la cadena de trazabilidad y por qué las dos taxonomías (`product.category` vs `mc.rov.subtipo`) se mantienen separadas están en [`docs/inventario.md`](docs/inventario.md). Relevante antes de tocar `linea_falla_ids` o de proponer unificar catálogos.
- Versión del módulo: `19.0.1.5.0`

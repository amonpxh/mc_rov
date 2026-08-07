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

Estrategia: **GitHub Flow simplificado**. Estado actual: desarrollador único con despliegue directo a producción — bus factor 1, que **Phase -1 del pipeline roadmap está diseñada para resolver** (ver [`docs/pendientes.md`](docs/pendientes.md)). Mantener disciplina de PR desde ya para que el flujo esté en su lugar cuando se sume un colega.

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

## Estado actual

Trabajo pendiente y diseños ya acordados: ver [`docs/pendientes.md`](docs/pendientes.md). Actualizar ese archivo al cerrar cada sesión de trabajo.

## Notas técnicas

- `ultima_mantencion` en `stock.lot` usa `fecha_entrega_real` de la última orden `done` **de tipo `mantencion_preventiva`**, ingresada por el técnico al cerrar la orden. Las correctivas no cuentan: un equipo reparado sigue debiendo su mantención anual.
- Una orden de reparación puede tener **varios tipos de intervención** (`tipo_intervencion_ids`): una visita al taller puede ser mantención y reparación a la vez. Lo que define de qué cuenta son las casillas `es_mantencion` y `es_reparacion` del tipo, no su nombre — nunca comparar contra el string `"mantencion_preventiva"` en código nuevo. Son independientes: un diagnóstico no lleva ninguna de las dos.
- El ciclo de mantención parte de `mc_fecha_puesta_servicio` y se reinicia con cada mantención cerrada. Su largo está en el parámetro de sistema `mc_rov.meses_ciclo_mantencion` (default 12), no en el código. **Sin fecha de puesta en servicio no hay reloj**, a propósito: los equipos en bodega no deben aparecer en la lista de vencidos.
- No existe un booleano "mantención vencida" almacenado, y no debe agregarse: un equipo se vence por el paso del tiempo, no porque alguien lo edite, así que quedaría desactualizado en silencio. El filtro compara `proxima_mantencion` contra la fecha de hoy.
- Al cerrar una orden, `fecha_entrega_real` se sella sola si está vacía. De eso dependen `ultima_mantencion` y `ultima_reparacion`; antes quedaba en blanco y el trabajo no contaba, sin ningún aviso.
- `mc_estado_operativo` se deriva de las órdenes abiertas del equipo (`repair_ids`), no se escribe a mano. Los borradores no cuentan — una orden en draft es una cotización y el equipo todavía no entró al taller. Misma convención que `mc_repair_count`.
- **Patrón recurrente en este módulo:** varios campos de `stock.lot` eran copias manuales de información que ya vivía en otro registro (`es_un_rov` ↔ categoría del producto, `mc_estado_operativo` ↔ órdenes de reparación). El síntoma es siempre el mismo: el dato se desincroniza y nada lo detecta. Antes de agregar un campo manual a `stock.lot`, verificar si la respuesta ya está en otro modelo.
- El dominio `[('componente_id', '=', componente_id)]` en `subtipo_id` dentro del one2many editable funciona correctamente desde Odoo 17+.
- Los campos de ficha técnica en `stock.lot` reemplazaron los `x_studio_*` de Studio. Los campos Studio siguen en la BD como columnas huérfanas — se pueden eliminar desde Studio o vía SQL cuando se confirme que no hacen falta.
- **Patrón de migración**: el ORM de Odoo crea las columnas nuevas **antes** de ejecutar el script `post-migrate.py`. Por eso las migraciones de renombrado deben usar `UPDATE SET nuevo = viejo` + `DROP COLUMN viejo`, no `RENAME COLUMN` (que falla porque la columna destino ya existe).
- `es_un_rov` en `stock.lot` se deriva de la categoría del producto (`child_of` sobre la raíz de vehículos). La raíz se resuelve del parámetro de sistema `mc_rov.rov_category_id`, con respaldo al XML ID `__import__.cat_ROV`. **Si la raíz no resuelve, todos los equipos quedan marcados como no-ROV y se ocultan sus cuatro pestañas de ficha técnica** — el compute lo registra como `ERROR` en el log en vez de lanzar excepción, porque fallar dejaría inaccesible toda la vista de lotes, incluidos los que no son ROV. Si alguien reporta que "desapareció la ficha técnica", revisar el log antes que el código.
- El `depends` de `es_un_rov` escucha `product_id.categ_id`, que no cubre que una categoría cambie de padre. Ese hueco lo tapa el override de `write` en `models/product_category.py`.
- **Operación en producción:** ver [`docs/runbooks/deploy.md`](docs/runbooks/deploy.md) — incluye comandos de deploy, verificación, y rollback.
- **Correr tests:** ver [`docs/runbooks/testing.md`](docs/runbooks/testing.md) — incluye sintaxis `--test-tags` y gotchas de Odoo 17+.

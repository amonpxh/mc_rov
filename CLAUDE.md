# mc_rov — Módulo Odoo para Gestión de ROVs (Marine Connection)

## Descripción

Módulo Odoo 19 que extiende `repair` para gestionar reparaciones y mantenciones de equipos ROV (Remotely Operated Vehicles). Desarrollado para Marine Connection.

**Dependencias:** `stock`, `repair`, `sale`, `sale_renting`

## Estructura del módulo

```
mc_rov/
├── models/
│   ├── mc_rov_componente.py        # Modelos propios: componente, subtipo, acción, línea de falla
│   ├── repair_order.py             # Herencia de repair.order
│   └── stock_lot.py                # Herencia de stock.lot
├── views/
│   ├── mc_rov_componente_views.xml # Lista + formulario de componentes y acciones
│   ├── repair_order_views.xml      # Herencia formulario repair.order
│   ├── stock_lot_views.xml         # Herencia formulario stock.lot
│   └── mc_rov_menus.xml            # Menú en configuración de reparaciones
├── data/
│   └── mc_rov_data.xml             # Datos maestros: 10 acciones + 8 componentes + ~40 subtipos
├── security/
│   └── ir.model.access.csv         # Accesos a los 4 modelos propios
├── static/src/css/
│   └── mc_rov.css                  # Mejora visual de campos editables
├── .github/workflows/lint.yml      # CI: lint automático en push
├── .pre-commit-config.yaml         # Hooks de pre-commit (pylint-odoo)
└── __manifest__.py
```

## Modelos implementados

### Propios
| Modelo | Descripción |
|--------|-------------|
| `mc.rov.componente` | Catálogo de componentes ROV (Motor, Umbilical, Electrónica, etc.) |
| `mc.rov.subtipo` | Subtipos por componente (Rotor, Hélice, ESC, etc.) |
| `mc.rov.accion` | Catálogo de acciones en intervenciones (Reparación, Limpieza, Soldadura, etc.) |
| `mc.rov.linea.falla` | Líneas de trabajo registradas en una orden de reparación |

### Heredados
| Modelo base | Campos añadidos |
|------------|----------------|
| `repair.order` | `tipo_intervencion`, `item_2..5`, `falla_reportada`, `linea_falla_ids`, `estado_final`, `causa_raiz`, `garantia_reparacion`, `fecha_garantia`, `fecha_entrega_real`, `observaciones_salida` |
| `stock.lot` | `es_un_rov`, `mc_estado_comercial`, `mc_estado_operativo`, `mc_repair_count` (computed), `ultima_mantencion` (computed), `action_ver_reparaciones`, + 48 campos de ficha técnica ROV con prefijo `mc_` (especificaciones, periféricos, umbilical, prueba en terreno) |

## Datos maestros incluidos

**Acciones (10):** Cambio completo, Cambio de componente, Reparación, Mantención preventiva, Limpieza, Calibración, Configuración / Software, Soldadura, Sin solución, Derivado a fabricante

**Componentes (8):** Motor, Umbilical, Electrónica / Software, Estructura / Chasis, Consola, Cámara, Sensor, Otro

**Subtipos por componente:**
- Motor: Rotor, Bobina/Núcleo, Hélice, Tobera, Buje, ESC, Cable de motor, Motor completo
- Umbilical: Conector submarino, Conector volante, Mufa, Cable, Aislación, Neutrik
- Electrónica: Micro SD, Fuente de poder, ESC electrónico, Tarjeta de comunicación, Raspberry/NUC, Navigator, Parámetros/Configuración, PCB/Placa
- Estructura: Domo, Chasis, Soldadura/Abrazadera, Mangueras, Penetrador, O-ring/Sello, Brazo/Pinza, Flotabilidad
- Consola: Monitor, Conector, NUC/PC, Joystick, Teclado, Ventilador, Cable HDMI/Splitter
- Cámara: Base/Máscara, Módulo cámara, Tilt, Domo/Lente, Cable interno
- Sensor: Sensor de presión, Compás/IMU, Sensor de temperatura, Sensor de leak, USBL/Beacon

## Convenciones de código

Los comentarios deben explicar el **por qué**, no repetir lo que el código ya dice. Se espera:
- Docstring de clase en cada modelo explicando su rol en el dominio
- Comentario en campos cuyo propósito no sea obvio por el nombre
- Comentario en métodos `compute` y `onchange` explicando la lógica de negocio
- En herencias, indicar brevemente qué se extiende y la razón

## Flujo de trabajo con git

Estrategia: **GitHub Flow simplificado** (desarrollador único, despliegue directo a producción).

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

### Completado
- [x] Estructura base del módulo: manifest, `__init__.py`, dependencias
- [x] Modelo `mc.rov.componente` con subtipos anidados y campo `active`
- [x] Modelo `mc.rov.linea.falla`: secuencia, componente, subtipo filtrado, acción y detalle
- [x] Modelo `mc.rov.accion`: catálogo configurable de acciones (Reparación, Limpieza, etc.) con menú en Reparaciones > Configuración; reemplaza el campo Selection anterior
- [x] Herencia `repair.order`: tipo de intervención, ítems del sistema, falla reportada, pestañas "Trabajos realizados" y "Resultado"
- [x] Herencia `stock.lot`: botón inteligente de reparaciones, `ultima_mantencion`, acción de historial
- [x] Vistas de componentes (lista y formulario con subtipos inline)
- [x] Herencia de vistas: formularios de `repair.order` y `stock.lot`
- [x] Menú "Componentes ROV" bajo Reparaciones > Configuración
- [x] Reglas de acceso para los 3 modelos propios (CRUD sin restricción de grupo)
- [x] Datos maestros: 8 componentes y ~40 subtipos predefinidos
- [x] CSS personalizado para mejorar visibilidad de campos editables (excluye checkbox y radio)
- [x] Flujo de trabajo con ramas (GitHub Flow) documentado y rama `develop` creada
- [x] `.gitignore` completo (Python, Odoo, editores, sistema)
- [x] `pre-commit` con `pylint-odoo` configurado (`.pre-commit-config.yaml`)
- [x] GitHub Actions CI: lint automático en push a `main`/`develop`
- [x] Convención de versionado semántico del módulo documentada
- [x] Docstrings y comentarios inline en los tres modelos
- [x] Campo `es_un_rov` definido en el módulo (reemplaza `x_studio_es_un_rov` de Studio; dato migrado en producción, campo Studio eliminado)
- [x] Tests de `stock.lot`: 8 tests cubriendo `es_un_rov`, `mc_repair_count` y `ultima_mantencion` (todos pasando en `odoo_test`)
- [x] Ficha técnica ROV migrada de Studio al módulo: 48 campos propios en `stock.lot` (especificaciones, periféricos, umbilical, prueba en terreno), con script de migración de datos (`migrations/19.0.1.1.0/post-migrate.py`) — versión `19.0.1.1.0`
- [x] Vista de Studio eliminada de la BD; toda la lógica de visibilidad controlada por `es_un_rov` en el módulo
- [x] Botón duplicado de reparaciones eliminado (el módulo `repair` ya provee el suyo)
- [x] Prefijo `mc_` en los 48 campos de ficha técnica y `mc_repair_count` en `stock.lot`; migración `19.0.1.2.0` aplicada y verificada en producción (48 columnas `mc_*` confirmadas en BD) — versión `19.0.1.2.0`
- [x] Flujo de ramas GitHub Flow estrenado: primer `feature/` branch mergeado a `main` con PR flow completo
- [x] Vista lista de `repair.order` con columnas `tipo_intervencion` y `estado_final` (antes de la columna estado)
- [x] `ultima_mantencion` corregida: ahora usa `fecha_entrega_real` (campo propio del módulo) en vez de `create_date`
- [x] Tests de `repair.order`: 10 tests cubriendo defaults, selecciones, `fecha_entrega_real` y `linea_falla_ids` (todos pasando en `odoo_test`)
- [x] Migración `19.0.1.1.0` corregida: segundo guard evita fallo en `odoo_test` y reinstalaciones donde las columnas intermedias sin prefijo `mc_` no existen
- [x] Tests de `mc.rov.componente`: 16 tests cubriendo `mc.rov.componente`, `mc.rov.subtipo`, `mc.rov.accion` y `mc.rov.linea.falla` (todos pasando en `odoo_test`)
- [x] XPaths frágiles en `stock_lot_views.xml` corregidos: `//field[@name='ref']` → `//field[@name='product_id']`; `//group[@name='main_group']` → `//sheet` (ambos son anclajes estables independientes de la estructura interna de Odoo)
- [x] Campos `fecha` y `horas` agregados a `mc.rov.linea.falla`; vista "Trabajos realizados" muestra columnas Componente, Subtipo, Acción, Fecha, HH., Detalle — versión `19.0.1.3.0`, verificado en producción, 43 tests pasando

### Pendiente
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

## Notas técnicas

- `ultima_mantencion` en `stock.lot` usa `fecha_entrega_real` de la última orden `done`, ingresada por el técnico al cerrar la orden.
- El dominio `[('componente_id', '=', componente_id)]` en `subtipo_id` dentro del one2many editable funciona correctamente desde Odoo 17+.
- Los campos de ficha técnica en `stock.lot` reemplazaron los `x_studio_*` de Studio. Los campos Studio siguen en la BD como columnas huérfanas — se pueden eliminar desde Studio o vía SQL cuando se confirme que no hacen falta.
- **Patrón de migración**: el ORM de Odoo crea las columnas nuevas **antes** de ejecutar el script `post-migrate.py`. Por eso las migraciones de renombrado deben usar `UPDATE SET nuevo = viejo` + `DROP COLUMN viejo`, no `RENAME COLUMN` (que falla porque la columna destino ya existe).
- Ruta del módulo en producción: `/opt/odoo/custom-addons/mc_rov`
- Base de datos de producción: `odoo_prod`
- Log de Odoo en producción: `/var/log/odoo/odoo-server.log`
- Configuración de Odoo: `/etc/odoo/odoo.conf`
- Para actualizar el módulo en producción:
  ```bash
  cd /opt/odoo/custom-addons/mc_rov && git pull origin main
  sudo -u odoo odoo -u mc_rov --stop-after-init --no-http --config /etc/odoo/odoo.conf
  sudo systemctl restart odoo
  ```
- Para verificar que la actualización quedó OK:
  1. `tail -20 /var/log/odoo/odoo-server.log` — sin líneas `ERROR`, registry cargado
  2. En Odoo: navegar a la sección afectada y confirmar visualmente que funciona
- **Formato de `--test-tags` en Odoo 17+**: la sintaxis correcta es `/modulo:Clase` (no `modulo.Clase`). Ejemplos:
  ```bash
  # Todos los tests del módulo
  sudo -u odoo odoo -d odoo_test -u mc_rov --test-tags /mc_rov --stop-after-init --no-http --config /etc/odoo/odoo.conf
  # Una clase específica
  sudo -u odoo odoo -d odoo_test -u mc_rov --test-tags /mc_rov:TestMcRovComponente --stop-after-init --no-http --config /etc/odoo/odoo.conf
  ```
  Siempre incluir `-u mc_rov` o los tests no se descubren.
- Versión del módulo: `19.0.1.3.0`

# mc_rov — Módulo Odoo para Gestión de ROVs (Marine Connection)

## Descripción

Módulo Odoo 19 que extiende `repair` para gestionar reparaciones y mantenciones de equipos ROV (Remotely Operated Vehicles). Desarrollado para Marine Connection.

**Dependencias:** `stock`, `repair`, `sale`, `sale_renting`

## Estructura del módulo

```
mc_rov/
├── models/
│   ├── mc_rov_componente.py        # Modelos propios: componente, subtipo, línea de falla
│   ├── repair_order.py             # Herencia de repair.order
│   └── stock_lot.py                # Herencia de stock.lot
├── views/
│   ├── mc_rov_componente_views.xml # Lista + formulario de componentes
│   ├── repair_order_views.xml      # Herencia formulario repair.order
│   ├── stock_lot_views.xml         # Herencia formulario stock.lot
│   └── mc_rov_menus.xml            # Menú en configuración de reparaciones
├── data/
│   └── mc_rov_data.xml             # Datos maestros: 8 componentes + ~40 subtipos
├── security/
│   └── ir.model.access.csv         # Accesos a los 3 modelos propios
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
| `mc.rov.linea.falla` | Líneas de trabajo registradas en una orden de reparación |

### Heredados
| Modelo base | Campos añadidos |
|------------|----------------|
| `repair.order` | `tipo_intervencion`, `item_2..5`, `falla_reportada`, `linea_falla_ids`, `estado_final`, `causa_raiz`, `garantia_reparacion`, `fecha_garantia`, `fecha_entrega_real`, `observaciones_salida` |
| `stock.lot` | `es_un_rov`, `estado_comercial`, `estado_operativo`, `repair_count` (computed), `ultima_mantencion` (computed), `action_ver_reparaciones`, + 40 campos de ficha técnica ROV (especificaciones, periféricos, umbilical, prueba en terreno) |

## Datos maestros incluidos

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
- [x] Tests de `stock.lot`: 8 tests cubriendo `es_un_rov`, `repair_count` y `ultima_mantencion` (todos pasando en `odoo_test`)
- [x] Ficha técnica ROV migrada de Studio al módulo: 44 campos propios en `stock.lot` (especificaciones, periféricos, umbilical, prueba en terreno), con script de migración de datos (`migrations/19.0.1.1.0/post-migrate.py`) — versión `19.0.1.1.0`
- [x] Vista de Studio eliminada de la BD; toda la lógica de visibilidad controlada por `es_un_rov` en el módulo
- [x] Botón duplicado de reparaciones eliminado (el módulo `repair` ya provee el suyo)

### Pendiente
- [ ] **Campos Selection con `widget="radio"`**: una vez seleccionada una opción no se puede desmarcar. Quitar `widget="radio"` para usar el dropdown estándar que permite limpiar la selección
- [ ] **`ultima_mantencion`**: actualmente usa `create_date` de la orden; debería usar una fecha real de cierre (`schedule_date` u otro campo dedicado)
- [ ] **Vista lista de `repair.order`**: heredar para añadir columnas `tipo_intervencion` y `estado_final`
- [ ] **Grupos de seguridad**: los accesos actuales son sin grupo — definir roles si se requiere control por perfil
- [ ] **Tests**: solo existen para `stock.lot` — faltan tests para `repair.order` y `mc.rov.componente`

## Notas técnicas

- `ultima_mantencion` en `stock.lot` usa `create_date` de la última orden `done`. Cuando exista un campo de fecha real de cierre en `repair.order`, actualizar aquí.
- El dominio `[('componente_id', '=', componente_id)]` en `subtipo_id` dentro del one2many editable funciona correctamente desde Odoo 17+.
- Los campos de ficha técnica en `stock.lot` reemplazaron los `x_studio_*` de Studio. Los campos Studio siguen en la BD como columnas huérfanas — se pueden eliminar desde Studio o vía SQL cuando se confirme que no hacen falta.
- Para actualizar el módulo en producción: `sudo -u odoo odoo -u mc_rov --stop-after-init --no-http --config /etc/odoo/odoo.conf`
- Versión del módulo: `19.0.1.1.0`

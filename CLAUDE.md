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
| `stock.lot` | `repair_count` (computed), `ultima_mantencion` (computed), botón inteligente, `action_ver_reparaciones` |

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
- [x] CSS personalizado para mejorar visibilidad de campos editables
- [x] Flujo de trabajo con ramas (GitHub Flow) documentado y rama `develop` creada

### Pendiente
- [ ] **`x_studio_es_un_rov`**: `stock_lot_views.xml` usa este campo de Studio para ocultar `ultima_mantencion`. Puede fallar si no existe en la instancia — evaluar si definirlo en el módulo o eliminar la condición
- [ ] **`ultima_mantencion`**: actualmente usa `create_date` de la orden; debería usar una fecha real de cierre (`schedule_date` u otro campo dedicado)
- [ ] **Comentarios en el código existente**: los modelos actuales no tienen docstrings ni comentarios — agregar en la próxima sesión que toque cada archivo
- [ ] **Vista lista de `repair.order`**: heredar para añadir columnas `tipo_intervencion` y `estado_final`
- [ ] **Reporte PDF**: informe de orden de reparación con trabajos realizados, resultado y garantía
- [ ] **Vista kanban**: seguimiento visual del estado de reparaciones en curso
- [ ] **Dashboard**: análisis por componente, causa raíz y tipo de intervención
- [ ] **Grupos de seguridad**: los accesos actuales son sin grupo — definir roles si se requiere control por perfil
- [ ] **Tests**: no existen pruebas unitarias ni de integración

## Notas técnicas

- `ultima_mantencion` en `stock.lot` usa `create_date` de la última orden `done`. Cuando exista un campo de fecha real de cierre en `repair.order`, actualizar aquí.
- El dominio `[('componente_id', '=', componente_id)]` en `subtipo_id` dentro del one2many editable funciona correctamente desde Odoo 17+.
- Versión del módulo: `19.0.1.0.0`

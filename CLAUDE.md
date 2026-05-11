# mc_rov — Módulo Odoo para Gestión de ROVs (Marine Connection)

## Descripción

Módulo Odoo 19 que extiende el módulo `repair` para gestionar reparaciones y mantenciones de equipos ROV (Remotely Operated Vehicles). Desarrollado para Marine Connection.

**Dependencias:** `stock`, `repair`, `sale`, `sale_renting`

## Estructura del módulo

```
mc_rov/
├── models/
│   ├── mc_rov_componente.py   # Modelos propios: componente, subtipo, línea de falla
│   ├── repair_order.py        # Herencia de repair.order
│   └── stock_lot.py           # Herencia de stock.lot
├── views/
│   ├── mc_rov_componente_views.xml  # Lista + formulario de componentes
│   ├── repair_order_views.xml       # Herencia formulario repair.order
│   ├── stock_lot_views.xml          # Herencia formulario stock.lot
│   └── mc_rov_menus.xml             # Menú en configuración de reparaciones
├── data/
│   └── mc_rov_data.xml        # Datos maestros: 8 componentes + ~40 subtipos
├── security/
│   └── ir.model.access.csv    # Accesos a los 3 modelos propios
├── static/src/css/
│   └── mc_rov.css             # Mejora visual de campos editables
└── __manifest__.py
```

## Modelos implementados

### Propios
| Modelo | Descripción |
|--------|-------------|
| `mc.rov.componente` | Catálogo de componentes ROV (Motor, Umbilical, Electrónica, etc.) |
| `mc.rov.subtipo` | Subtipos por componente (Rotor, Hélice, ESC, etc.) |
| `mc.rov.linea.falla` | Líneas de trabajo en una orden de reparación |

### Heredados
| Modelo base | Campos añadidos |
|------------|----------------|
| `repair.order` | `tipo_intervencion`, `item_2..5`, `falla_reportada`, `linea_falla_ids`, `estado_final`, `causa_raiz`, `garantia_reparacion`, `fecha_garantia`, `fecha_entrega_real`, `observaciones_salida` |
| `stock.lot` | `repair_count` (computed), `ultima_mantencion` (computed), botón inteligente + acción `action_ver_reparaciones` |

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

## Estado actual

### Completado
- [x] Estructura base del módulo con manifest, `__init__.py` y dependencias
- [x] Modelo `mc.rov.componente` con subtipos anidados y campo `active`
- [x] Modelo `mc.rov.linea.falla` con secuencia, componente, subtipo (filtrado por componente), acción y detalle
- [x] Herencia `repair.order`: tipo de intervención, ítems del sistema (item_2..5), falla reportada, pestaña "Trabajos realizados", pestaña "Resultado" con estado final / causa raíz / garantía
- [x] Herencia `stock.lot`: botón inteligente de reparaciones, campo `ultima_mantencion`, acción para ver historial
- [x] Vistas de componentes (lista y formulario con subtipos inline)
- [x] Herencia de vistas: formulario `repair.order` y formulario `stock.lot`
- [x] Menú "Componentes ROV" bajo Reparaciones > Configuración
- [x] Reglas de acceso para los 3 modelos propios (CRUD sin restricción de grupo)
- [x] Datos maestros: 8 componentes y ~40 subtipos predefinidos
- [x] CSS personalizado para mejorar visibilidad de campos editables

### Pendiente / Por hacer
- [ ] **Campo `x_studio_es_un_rov`**: `stock_lot_views.xml` referencia este campo de Studio en el `invisible` de `ultima_mantencion`. Puede fallar si el campo no existe en la instancia destino — evaluar si crear el campo en el módulo o eliminar la condición
- [ ] **Reportes PDF**: Informe de orden de reparación con los campos propios del módulo (trabajos realizados, resultado, garantía)
- [ ] **Vista lista personalizada de `repair.order`**: Añadir columnas `tipo_intervencion` y `estado_final` a la lista heredada
- [ ] **Vista kanban de órdenes**: Útil para seguimiento visual del estado de reparaciones
- [ ] **Campo `fecha_completada` en `stock.lot`**: `ultima_mantencion` actualmente usa `create_date` de la orden; debería usar una fecha real de cierre de la reparación
- [ ] **Dashboard o estadísticas**: Vista de análisis por componente, causa raíz, tipo de intervención
- [ ] **Tests**: No existen pruebas unitarias ni de integración
- [ ] **Grupos de seguridad**: Los accesos actuales son sin restricción de grupo (público) — definir grupos propios si se necesita control de acceso por rol
- [ ] **Menú principal propio**: El módulo usa el menú de Reparaciones como padre; podría necesitar un menú de aplicación propio si Marine Connection quiere separarlo

## Flujo de trabajo con git

Estrategia: **GitHub Flow simplificado** (desarrollador único, despliegue directo a producción).

```
main      ──●──────────────────────●──→  producción (Odoo server)
             │                     ↑
feature/X    └──●──●──●────────────┘
fix/Y              └──●──●─────────┘
```

### Reglas
- `main` = siempre estable y desplegable. No commitear directamente salvo hotfixes triviales.
- `develop` = rama de integración opcional para agrupar features antes de subir a main.
- Toda funcionalidad nueva → rama desde `main` (o `develop`), merge al terminar.
- Después de merge a `main`: `git push origin main` y actualizar el módulo en el servidor Odoo.

### Nomenclatura de ramas
| Tipo | Formato | Ejemplo |
|------|---------|---------|
| Nueva función | `feature/<nombre>` | `feature/reporte-pdf-reparacion` |
| Corrección | `fix/<nombre>` | `fix/ultima-mantencion-fecha-real` |
| Refactor | `refactor/<nombre>` | `refactor/grupos-seguridad` |

### Ciclo de vida de una tarea
```bash
git checkout main && git pull          # partir desde main actualizado
git checkout -b feature/mi-funcion     # crear rama
# ... desarrollar y commitear ...
git checkout main
git merge feature/mi-funcion
git push origin main                   # → actualizar módulo en servidor Odoo
git branch -d feature/mi-funcion       # limpiar rama local
```

---

## Notas técnicas

- `ultima_mantencion` en `stock.lot` usa `create_date` de la última orden en estado `done`. Si la orden tiene una fecha de cierre real, conviene crear un campo `date_done` en `repair.order` y usarlo aquí.
- El dominio en `subtipo_id` dentro del one2many editable (`domain="[('componente_id', '=', componente_id)]"`) depende del contexto de fila — comportamiento correcto en Odoo 17+.
- Versión del módulo: `19.0.1.0.0`

# Inventario desde el Centro de trabajo

El botón **Inventario** abre cinco secciones dentro del Centro. Se utilizan los registros,
acciones y vistas nativas de Odoo; las existencias son las mismas que en la aplicación Inventario.

| Sección | Accesos | Uso |
| --- | --- | --- |
| Existencias | Existencias | Consultar cantidades, reservas, ubicación, serie e historial. Parte de ubicaciones internas. |
| Productos | Productos y Variantes | Consultar el catálogo, incluidos materiales y repuestos; crear o editar si los permisos lo permiten. |
| Series y lotes | Series y lotes | Consultar identificación, ubicación y trazabilidad. Crear una serie no ingresa stock por sí solo. |
| Operaciones | Recepciones, Entregas, Traslados internos, Conteos y ajustes | Abrir el flujo logístico o de conteo nativo correspondiente. |
| Reabastecimiento | Reabastecimiento | Revisar necesidades y reglas mediante la herramienta nativa. |

**Abrir Inventario completo** cambia a la aplicación y muestra sus menús completos, incluidos
reportes y configuración disponibles para la cuenta.

## Permisos

- Se necesita una cuenta interna con acceso a Inventario. El Centro no concede permisos nuevos.
- Reabastecimiento requiere el grupo nativo de responsable de Inventario, como su menú original.
- Variantes, series/lotes y traslados internos respetan las funciones habilitadas de Odoo.
- Crear o editar depende de los permisos del modelo; tener acceso a la consulta no concede altas.
- Las consultas y operaciones conservan las empresas activas. No existe un filtro exclusivo ROV
  en el catálogo de materiales y repuestos.

## Navegación y actualización

Cada destino conserva sus filtros y tipo de vista dentro del Centro. Al abrir un formulario
nativo y volver, se retoma el mismo espacio. Los cambios sin guardar conservan la confirmación
de salida nativa. **Actualizar** mantiene la búsqueda y descarta los datos locales anteriores.

Cambiar a **Inventario completo** usa la navegación nativa entre aplicaciones y limpia la pila
de acciones. Atrás del navegador puede reconstruir el Centro en su espacio inicial de Trabajo
asignado; no equivale a volver desde un formulario de ese Centro.

Conteos y Reabastecimiento pueden ejecutar mantenimiento nativo al abrirse. Validar un movimiento,
aplicar un ajuste o lanzar un aprovisionamiento tiene los efectos normales de Inventario.
El acceso no configura rutas, mínimos, proveedores, compras ni automatismos de actividades.

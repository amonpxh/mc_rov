# Inventario operativo dentro del Centro

Aprobación del usuario: «ok go» a la propuesta de cinco áreas: Existencias, Productos, Series/lotes, Operaciones y Reabastecimiento, con variantes dentro de Productos y acceso a Inventario completo.

Base: main/producción28c5cde19.0.25.3.0; CI837/837 y navegador39/39. STAGING conserva la implementación anterior con versión instalada19.0.25.2.0. Rama nueva feature/work-center-inventory-workspace en checkout aislado existente; rama anterior preservada.

## Comportamiento

- El botón principal Inventario abrirá un espacio del Centro, conservando los ocho botones y su distribución2/4/8.
- Existencias usa la vista nativa, inicialmente filtrada a ubicaciones internas; cantidades, reservas, ubicación, series e historial.
- Productos ofrece catálogo nativo y variantes; altas/edición se rigen por permisos existentes, sin filtro exclusivo ROV.
- Series/lotes ofrece catálogo nativo y trazabilidad. Crear una serie no representa por sí solo una entrada de stock.
- Operaciones ofrece recepciones, entregas, traslados internos y conteos/ajustes físicos. No inventar tipos de operación ni ubicaciones; respetar almacén y empresas activas.
- Reabastecimiento reutiliza el flujo nativo, incluida su lógica y restricciones. No configura rutas, mínimos ni compras automáticamente.
- Abrir Inventario completo debe seleccionar la aplicación nativa y su navegación, no simular que una lista aislada contiene todos los menús.
- Tablas/vistas nativas para evitar una segunda gestión de stock. Cada destino comprueba grupo, permiso del modelo, empresas y restricciones propias del destino. Sin sudo de existencias ni acceso técnico nuevo a acciones/menús.
- Conservar filtros por sección, protección de edición sin guardar, estado al volver, errores recuperables y protección de doble apertura.
- Listas nativas pueden tener mantenimiento propio; no prometer que abrirlas siempre es SQL solo lectura. Auditoría inicial sí es solo lectura y no ejecuta acciones.

## Límites

Sin nuevos modelos de inventario, estados logísticos, permisos, cuentas, datos QA persistentes, reglas de reabastecimiento ni automatismos nuevos. No sustituye Compras ni configura proveedores. Calendarios, PDFs y producción intactos durante desarrollo; publicación/merge/despliegue posteriores se revisan como entrega nueva.

## Decisiones técnicas pendientes de fuentes instaladas

Identificadores y tipos de acciones, restricciones de grupos, necesidad de acciones servidor o métodos nativos de reabastecimiento, apertura real de la aplicación y reutilización segura de vistas embebidas. Estas decisiones se contrastan con Odoo instalado antes de escribir producto.

## Auditoría instalada confirmada y contrato del servicio

Auditoría READ ONLY+rollback confirmada:8modelos,39accionesventana,53menús. Los hashes del producto coinciden exactamente con la fuente verificada en la suite837 anterior; sin deriva. Versión instaladaSTAGING19.0.25.2.0, servicioactivo. Matriz de cuenta interna activa: stockmanager con variantes/series/múltiplesubicaciones; no habilitar grupos nuevos para ampliar accesos.

El servicio nuevo expone get_inventory_destinations(), action_inventory_destination(key) y get_inventory_application(). Nueve claves en cinco secciones; DTO con key/section/available/can_create sin contar existencias. Acciones de catálogo normalizan contexto/dominio conservando defaults nativos, vistas y empresas activas. No reutilizar el helper ROV que elimina búsquedas por defecto y fuerza list/form.

Productos stock.product_template_action_product; variantes stock.stock_product_normal_action; series stock.action_production_lot_form. Recepciones/entregas/internos usan métodos get_action_picking_tree_incoming/outgoing/internal de stock.picking. Conteos usa stock.quant.action_view_inventory; existencias conserva action_inventory previo. Reabastecimiento usa método nativo action_open_orderpoints con cuatro defaults manuales auditados; requiere stock.group_stock_manager aunque stockuser tenga ACL de lectura de orderpoints. Variantes/series/internos respetan featuregroups nativos. Abrir Inventario completo usa root stock.menu_stock_root mediante menu.selectMenu, cuya navegación cambia la aplicación; no leer menús técnicos ni simular solo una acción de lista.

get_inventory_application devuelve solo menu_id al usuario autorizado; get_inventory_destinations no llama mantenimiento de quants ni reabastecimiento. Native abrir conteos/reabastecimiento puede mantener datos por diseño de Odoo; comprobar operación con escenario de QA antes de entrega, sin prometer solo lectura al abrir.

Retener action_inventory previo para compatibilidad; el overview debe mantener acceso al espacio si un destino permitido existe aunque el modelo de quants no sea accesible. UI cambia intencionalmente la selección del botón principal a panel: actualizar las pruebas previas de apertura directa para preservar su intención sobre el subdestino Existencias, no eliminar su cobertura. Caché de vistas/filtros debe respetar empresas activas y no reinyectar contextos de compañías previas al cambiar selección.

## Retorno entre formularios y aplicaciones

El Centro conserva selección, filtros y vistas al alternar sus secciones o volver desde un formulario nativo dentro de su pila de acciones. Abrir Inventario completo selecciona la aplicación con la navegación nativa, que limpia esa pila. Atrás del navegador después de cambiar de aplicación puede reconstruir el Centro en Trabajo asignado; no se añade persistencia paralela fuera de la pila nativa.

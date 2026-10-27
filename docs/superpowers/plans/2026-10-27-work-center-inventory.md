# Inventario y menú adaptable — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Abrir existencias nativas desde el Centro y organizar ocho accesos según el ancho disponible.

**Architecture:** Ampliar el servicio existente con capacidad de inventario y acción
nativa protegida; la navegación llama esa acción sin crear una nueva área de consulta
ROV. Grid adaptable con container queries y etiquetas cortas.

**Tech Stack:** Odoo19 ORM, Owl, HOOT, SCSS.

**Spec:** `docs/superpowers/specs/2026-10-27-work-center-inventory-design.md`

## Global Constraints

Sin nuevos permisos, sudo sobre existencias, stocks ficticios persistentes, cambios de
PDFs o producción. Base f5fd59f; preservar ediciones del usuario en otro worktree.
No reconstruir faltantes, compras ni automatismos en este cambio.

## Review Focus

- Llamada directa sin permiso o con contexto de empresas no autorizadas: rechazar antes de Odoo.
- Stock user sin lectura de acciones técnicas: debe abrir existencias sin requerir Administrador.
- Salida con edición sin guardar o petición fallida: conservar estado y protección de abandono.
- Ventana amplia con contenedor estrecho: distribuir por contenedor, no solo por viewport.
- Etiquetas largas, 320px y temas claro/oscuro: sin desbordes ni foco oculto.

### Task 1: Acceso nativo y permisos

**Files:** `tests/test_work_center_inventory.py`, `tests/__init__.py`,
`models/mc_rov_work_center.py`.

- [x] Pruebas primero: ocho contratos de capacidad/acción y un control del destino
  nativo. Conservar los21 existentes del Centro. RED nativo exacto: ocho fallos por
  ausencia de la funcionalidad;22 casos previos/control deben pasar.
- [x] Registrar fuentes nativas instaladas y garantizar restauración de pruebas,
  stocks/documentos/configuraciones y servicio tras el RED temporal en STAGING.
- [x] Implementar capacidad y acción con grupo/ACL/empresas activas, sin ampliar contexto.
- [x] GREEN nativo de30 casos; permisos técnicos y contexto de compañía incluidos.

### Task 2: Menú y navegación

**Files:** `static/src/work_center/work_center.js`, `work_center.xml`,
`work_center.scss`, `static/tests/work_center.test.js`.

- [x] Pruebas HOOT de botón autorizado/oculto, acción nativa, error, abandono con
  edición y retorno con estado; RED antes de implementación.
- [x] Botón nativo entre Calidad y Diseño; etiquetas cortas sin renombrar áreas. (STAGING y HOOT39 aprobados.)
- [x] Grid2/4/8 por contenedor; comprobar ocho accesos, filas y anchos iguales en
  320/480/1000/1600px y dentro de un panel estrecho; sin overflow.
- [x] Ejecutar HOOT existente y nuevo en navegador y comprobar ambos temas.

### Task 3: Entrega

- [ ] Regresión adecuada, lint, revisión final y evidencia. Reutilizar828 de base
  solo como baseline; el commit final debe validarse por CI y pruebas pertinentes.
- [x] QA en STAGING, limpieza de pruebas temporales y actualización de continuidad.
- [ ] PR adjunto/CI. Merge y producción requieren autorización posterior.

Verificación final nativa:837/837 exactos, HOOT39/39, restauración de pruebas y snapshot sin cambios. Revisión sin bloqueantes. Black99 y pylint10; post-regresión solo versión19.0.25.3.0 y formato backend AST idéntico. CI del commit final pendiente. Visual8columnas/foco opcional pendiente; geometría8 columnas comprobada por HOOT.

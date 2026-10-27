# Inventario operativo del Centro — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Dar acceso desde el Centro a cinco áreas nativas de Inventario sin ampliar permisos ni duplicar operaciones.

**Architecture:** Servicio de destinos/capacidades separado por responsabilidad, integrado en el Centro existente. Contenedor de vistas nativas reutilizable, con estado propio por sección y guard de edición. La selección de la aplicación completa usa la navegación nativa. Identificadores y permisos se fijan tras auditoría instalada.

**Tech Stack:** Odoo19 ORM, Owl, vistas nativas, HOOT y SCSS.

**Spec:** docs/superpowers/specs/2026-10-27-work-center-inventory-workspace-design.md

## Task 1: Fuentes y destinos seguros

Files: helper de auditoría local .tmp/work-center-inventory-workspace-pilot/source.py; nuevo tests/test_work_center_inventory_workspace.py; servicio models/work_center_inventory.py o extensión equivalente justificada tras auditoría; models/__init__.py si procede.

- [x] Auditar modelos/acciones/menús/ACL/métodos/configuración nativa instalada en READ ONLY+rollback, sin invocar acciones.
- [x] Definir tabla de destinos y capacidades, incluyendo variantes y cuatro tipos de operaciones; distinguir aperturas de consultas y operaciones que mantienen datos nativos.
- [x] Escribir contratos de permisos, contexto/empresas, restricción de acciones, IDs desconocidos, sin acceso técnico, sin consultas/cambios de stock para capacidades. Conservar nueve contratos previos y21Centro.
- [x] RED nativo exacto y restauración confirmada antes de producto.
- [x] Implementar mínimo y GREEN focalizado, con snapshot de stocks/configuración/PDF/historial intactos.

## Task 2: Espacio nativo y navegación

Files: static/src/work_center/work_center.js/xml/scss; componente inventory_workspace y vistas embebidas solo si mejora una responsabilidad real; tests/static existentes o módulo de pruebas dedicado con manifiesto actualizado.

- [x] Pruebas HOOT primero: cinco secciones, subdestinos, ACL, selección, acción nativa, crear/abrir registros, errores, carreras, retorno/filtros, edición sin guardar y aplicación completa.
- [x] RED observado en navegador; reutilizar controles nativos para búsqueda/agrupación/CRUD y vistas.
- [x] Implementar selección de Inventario dentro del Centro, estados por sección, operaciones y variantes, permisos y navegación completa.
- [x] GREEN, foco y temas claro/oscuro; tamaños estrecho/medio/amplio y vistas nativas sin romper el menú principal.

## Task 3: Cierre y entrega

- [x] Suite completa por nombres sobre el producto final, lint y revisión, evitando repetir suites sin cambios.
- [x] QA operativo en STAGING: apertura de vistas/formulario vacío descartado, aplicación completa y pruebas transaccionales con usuarios/stock nativos; sin escenario persistente ni reglas reales nuevas. Datos y pruebas temporales restaurados.
- [ ] Commit/PR/CI y actualizar continuidad. Publicación de rama nueva, merge y producción se decidirán después sobre entrega revisable; no reutilizar autorización PR109.

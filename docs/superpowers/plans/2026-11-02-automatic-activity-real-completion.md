# Cierre real de actividades automáticas Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans inline task-by-task. El usuario ya eligió implementación aquí y revisión independiente final. No repetir aprobación del alcance acordado.

**Goal:** Impedir que un cierre manual oculte trabajo automático abierto en los seis flujos, manteniendo cierres reales y actividades manuales intactas.
**Architecture:** Guard común externo a los hooks de mail.activity, identificación por enlaces privados autorizados y estado pendiente. Cierres reales siguen en sus servicios actuales; no hay asistente ni vía de retirada manual; tarjeta o referencia abren el documento sin botón redundante. Extensiones de vistas y store Mail nativos, sin reemplazar el Centro.
**Tech Stack:** Odoo19/Python/PostgreSQL, vistas XML y Owl/HOOT, ejecución SSH manual en STAGING.
**Spec:** docs/superpowers/specs/2026-11-02-automatic-activity-real-completion-design.md

## Global Constraints
- Cubrir reparación, fabricación, aceptación (cinco etapas), Calidad, Ingeniería e Inventario. Actividades manuales y aprobaciones PLM nativas intactas.
- No cambios en producción, cuentas reales, calendarios ni PDFs emitidos. QA wamR0o se conserva; no recrear escenarios.
- Permisos/empresas autorizan cada acción antes de consultar historial privado. Ni sudo ni contexto JSON autorizan cierre manual; proteger NewId y lotes mixtos.
- No reescribir manual_done históricos ni reconstruir pendientes pasados silenciosamente.
- No ofrecer ni permitir retirada manual a ningún rol. Decisión del usuario sustituye el alcance inicial de retirada excepcional; los72 tests/12paths locales se retiran explícitamente y sus instaladores se bloquean.

## Review Focus
1. Hook MRO escribe manual_done antes del guard: guard debe ejecutarse primero; probar todos los métodos y lotes mixtos.
2. Cierre real anidado pasa por cancel/unlink/archive: no bloquear los cierres ya registrados por servicios de negocio.
3. Chatter/global/formulario permiten vía que el Centro oculta: proteger servidor y todas las superficies.
4. Cuentas multiempresa/portal/tipos homónimos y temporales: no filtrar privados ni afectar actividades sin vínculo real.
5. Cierre simultáneo/archivo/reprogramación: bloqueo estable, fecha heredada y resultado coherente sin huérfanas.

### Task1: Servidor protege el trabajo pendiente
Files: tests/test_automatic_activity_completion.py (nuevo), models/automatic_activity_completion.py (nuevo, importado al final), models/__init__.py. Herramientas .tmp/automatic-activity-completion-pilot.
- [ ] Escribir60 casos: siete vías de bloqueo por cada flujo y tres controles por flujo (fixture propio pendiente, manual Todo y tipo propio sin run). Reutilizar fixtures nativos sin heredar clases que tengan tests.
- [ ] RED en STAGING con suite previa1120 completa +60:42 fallos nuevos previstos,1138 anteriores/controles verdes,0ERROR,1180 nombres únicos. Producto133 y snapshot entero intactos; retirar tests y reiniciar solo STAGING.
- [ ] Implementar identidad/comprobación/guard comunes al principio de _action_done, unlink y write(active=False); no confiar en identificación por título/tipo. Las callbacks de negocio con run ya cerrado pasan.
- [ ] GREEN focalizado60 + cierres reales seleccionados por nombre, incluidas todas las etapas de aceptación. Inventariar cada expectativa antigua de cierre manual incompatible y sustituirla explícitamente por bloqueo en Task2; no desactivar tests silenciosamente.
- [ ] Commit pequeño con evidencia nativa.

### Task2: Revisión de alcance e identidad de presentación
- [x] RED176 de retirada registrado; usuario descartó la función antes de instalarla. Restaurar únicamente12paths propios de producto y retirar72 tests que la exigían. Conservar guard104 instalado y evidencia anterior; bloquear viejos instaladores antes de SSH.
- [ ] RED de indicador mc_automatic_pending en seis flujos: propio pendiente, manual general, tipo propio sin run, NewId, store y fuente abierta sin cambios. Ausencia de asistente/gateway excepcional se conserva como control verde.
- [ ] Agregar indicador readonly/no almacenado y store de Mail con autorización actual; no abrir ACL a modelos privados ni bloquear filas para una lectura de presentación. No clasificar por título/tipo.
- [ ] Adaptar contratos antiguos incompatibles con mapa explícito, conservando permisos/auditoría. Nunca afirmar suite completa hasta revalidarla.

### Task3: Interfaz nativa abre el trabajo
Files: models/automatic_activity_completion.py (flags/store), views/mail_activity_views.xml, static/src/activity_completion/* (patch/XML), manifest assets, static/tests.
- [ ] Usar35 métodos/49 assets del recibo installed-source.json para mapear chatter, activity popover, global menu, native kanban/form/calendar/list y schedule-next.
- [ ] RED de flags autorizados/store y HOOT de cada superficie, actividad manual intacta, ausencia de retirada y acceso al origen. No crear APIs genéricas que lean privado ni un segundo motor UI.
- [ ] Ocultar Hecho/Cancelar de automáticas y no añadir Abrir redundante. Tarjeta/referencia/resumen accesible abren documento con acción nativa. En lista, acciones masivas de cierre solo para selección exclusivamente manual. Abrir nunca cierra ni guarda estados/stock.
- [ ] GREEN/temas/regreso y restauración temporal; commit.

### Task4: Integración y cierre
- [ ] Suite completa exacta con mapa de contratos reemplazados y nuevos; no reutilizar1120 como garantía del ajuste.
- [ ] Carreras resultado real/archivo/reprogramación, grupos/empresas y rollback; conservar los seis races stock anteriores.
- [ ] QA aislado con ambos roles y todos los procesos: negar cierre genérico, apertura correcta, completar por negocio, ausencia de retirada manual, plazos/historia. Antes de actualizar código compartido, conservar snapshot y detener/reiniciar controladamente solo servidor QA si hace falta; nunca reciclar su DB.
- [ ] Comparar en lectura deadline del parcial original/restante histórico y documentar caso no comprobado en pantalla. Conservar historial QA al cerrar.
- [ ] Informe de manual_done históricos sin reapertura automática; revisión independiente final, hooks, versión y CI/PR/merge. Producción requiere paquete concreto y autorización antes de instalar.

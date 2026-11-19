# Plan de implementación de F3

> Ejecución por tareas con superpowers:subagent-driven-development; cada tarea empieza con pruebas RED y termina con controles verificables.

**Objetivo** Medir la salida efectiva del taller respecto de compromisos acordados,
preservando promesa original, historial, alcance y acceso al origen.

**Arquitectura** Acciones explícitas de Venta, Reparación e Inventario, con modelos
privados para evidencias. Cálculo puro separado de la selección autorizada Odoo.
Interfaz en el tablero existente.

**Tecnología** Odoo 19, Python, Owl, pruebas transaccionales y HOOT.

**Diseño** [F3](../specs/2026-11-19-kpi-compromisos-cliente-design.md).

## Condiciones

Permisos efectivos del Supervisor y del documento nativo. No asignar usuarios ni
crear datos retroactivos. Conservar stock, flujos nativos y emitidos. Nunca deducir
salida física de una validación. Usar Santiago para límites por día.

## Tareas y comprobaciones

- [x] Promesas. Modelos privados `mc.rov.customer.commitment` y
  `mc.rov.customer.commitment.change` en `models/customer_commitment.py`.
  Origen autorizado, acción explícita, fecha precisa, series o cantidad y cambios
  trazables. Probar doble origen, Supervisor sin escritura, serie equivocada,
  reparaciones de servicio y pedido vinculado después de fijar.
- [x] Evidencia. Modelo `mc.rov.customer.dispatch` en
  `models/customer_dispatch.py`. Asistente en transferencia validada, con
  modalidad, fecha efectiva, constancia y autor. Probar corrección, retiro,
  pedido parcial, escritura sin acceso y transferencias internas.
- [x] Cálculo. `models/customer_commitment_metrics.py` con conciliación
  ordenada de salidas y devoluciones por serie, precisión de fecha y
  poblaciones distintas. Probar los ejemplos 8/10 y 8/9, reentrega, cambio
  tardío y falta de evidencia.
- [x] Consulta y presentación. `models/customer_commitment_kpi.py` filtra
  por origen, empresa y acceso a transferencias. Añadir F3 al tablero existente
  sin cambiar parámetros anteriores del RPC. Pruebas de entorno, categoría y
  permisos. Agregar vistas, asistentes e imports de forma conjunta.
- [ ] Validar. Pruebas puras, suite Odoo aislada, permisos, concurrencia,
  navegación, parciales y compatibilidad. La verificación que requiera servidor
  se hace en una copia QA autorizada o en CI del PR según corresponda.

## QA posterior a CI

- Reutilizar la copia de `odoo_test` del runner, con datos ficticios en empresa
  propia, correo y cron desactivados y navegador limitado al loopback.
- Sincronizar dos conexiones antes de registrar promesas y constancias. Comprobar
  duplicados, decisiones incompatibles, cambios, corrección frente a invalidación
  y rollback, con conteos y autores mediante una tercera conexión.
- Verificar en navegador los documentos nativos, los diálogos y la sección F3
  poblada, bajo Supervisor y una cuenta operativa sin ese grupo. Guardar el
  resultado de cada etapa en los artefactos del PR borrador.

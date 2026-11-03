# Preparación del uso real de Odoo

## Alcance autorizado

El usuario autorizó el 2026-11-03 adelantar KPI, Compras/abastecimiento, agente IA en
Odoo/Telegram, datos maestros, roles/permisos, procedimientos/capacitación, operación
técnica, ensayo general y plan de arranque. Se parte de producción19.0.25.6.0/main40ce2fe,
con los seis flujos de seguimiento instalados y configuración real aún pendiente.

Este programa contiene varios proyectos. Se ejecutan en la misma conversación, con
planes específicos cuando la auditoría permita fijar sus interfaces y pruebas.
Orden propuesto por Codex: KPI → Compras/abastecimiento → agente IA → preparación
operativa y ensayo general → arranque. La limpieza de datos y la documentación avanzan
en paralelo cuando no dependan de decisiones pendientes. No presupone un plazo.

## Arquitectura y límites

- Odoo conserva los registros operativos, permisos y empresas como fuente de verdad.
  Reutilizar las funciones nativas antes de crear módulos adicionales.
- Desarrollar y probar en STAGING o copias aisladas, con datos ficticios identificados.
  Conservar los datos actuales y la evidencia de las entregas anteriores.
- La autorización general permite auditar, diseñar, implementar y probar el alcance.
  No fija nombres de responsables, permisos reales, proveedores, importes de aprobación,
  credenciales de Telegram/IA, proveedor de modelos ni decisiones de contratación.
- Los cambios concretos en producción se presentan preparados y revisados antes de
  ejecutarlos. No activar políticas ni enviar mensajes, pedidos o pagos reales por defecto.
- No ampliar este programa a la sustitución de Defontana, SII o facturación. Esa etapa
  continúa separada y posterior a la estabilización operativa.
- Reutilizar el checkout ya aislado; implementación inline y revisión independiente
  de entregas sustanciales, siguiendo la preferencia de ejecución de esta conversación.

## Proyectos y resultados esperados

### 1. KPI

Auditar primero los seis historiales privados, sus fechas, identidad y permisos. Propuesta
inicial de Codex, pendiente de especificación detallada con los campos disponibles:
pendientes actuales, vencidos, cumplimiento del plazo, tiempo de resolución y
rechazos/reaperturas. Definir por indicador fórmula, población, fecha de corte, zona
horaria, filtros, exclusiones y cobertura. Valores desconocidos no equivalen a cero.

Separar el plazo original del reprogramado; cancelaciones, cierres manuales históricos
y pruebas QA no deben aparentar trabajo completado. Las cuentas compartidas no
identifican a la persona que ejecutó el trabajo. No inferir autoría desde el último
editor ni transformar acceso al tablero en acceso a historiales restringidos.

Fijar metas iniciales solo con acuerdo; validar la fórmula con casos ficticios y ajustar
su utilidad con experiencia real. El tablero debe permitir entender y abrir su evidencia
autorizada, sin duplicar estados ni crear otro sistema de tareas.

### 2. Compras y abastecimiento

Auditar módulos, solicitudes/cotizaciones a proveedores, órdenes, aprobaciones,
recepciones, parciales, devoluciones y reabastecimiento disponibles. Diseñar la relación
con necesidades de reparación/fabricación e Inventario. Una orden aprobada no equivale
a material recibido o disponible. No generar compras automáticas sin reglas explícitas.
Los responsables y umbrales de aprobación se acuerdan antes de configurar cuentas reales.

### 3. Agente IA

Auditar primero módulos IA, licencia y herramientas disponibles en esta instalación.
Diseñar identidad, permisos por empresa, auditoría y acciones permitidas antes de elegir
desarrollo propio o proveedor. Primer corte propuesto: consultas y resúmenes; después,
acciones validadas con los servicios de dominio existentes. Odoo y Telegram comparten
reglas, pero cada identidad debe estar vinculada explícitamente. Reintentos no duplican
acciones. No conceder administración global al agente ni leer credenciales en el chat.

### 4. Preparación operativa

- Datos maestros: informe de completitud y propuesta de carga para productos, variantes,
  series, componentes, BoM, proveedores y ubicaciones. No sobrescribir registros ni
  corregir cantidades reales a partir de supuestos o fixtures.
- Roles: matriz de consulta, ejecución, aprobación, reparto y reprogramación. Validar
  empresas y diferencias entre usuario/cuenta y empleado/persona.
- Procedimientos: recorridos breves por rol, con excepciones y criterio de cierre real.
- Operación técnica: comprobar respaldos/restauración, monitoreo y notificaciones;
  no asumir fallos de seguridad o infraestructura a partir de notas antiguas.
- Ensayo general: casos normales, rechazados, cancelados, parciales, fechas futuras,
  pausas y recuperación, con usuarios equivalentes a los reales y datos ficticios.
- Arranque: carga inicial reconciliada, fecha de corte, responsables, políticas elegidas,
  comprobación inicial, seguimiento y recuperación. Activación posterior y explícita.

## Primer corte ejecutable

Auditoría instalada de solo lectura en STAGING: modelo/campos/estados, fuentes nativas
seleccionadas, módulos/licencias identificables, grupos por XMLID, cobertura agregada
de datos maestros y calendario; sin valores de negocio individuales ni secretos.
La consulta debe usar transacción READ ONLY y rollback, proteger el conjunto de fuentes
instaladas y no instalar, reiniciar, crear datos, ejecutar acciones o modificar cron/correo.
La evidencia permite especificar el primer incremento de KPI y los siguientes dos proyectos.

# Preparación del uso real Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans inline task-by-task. El usuario autorizó el programa y conserva su preferencia de implementación aquí y revisión independiente final.

**Goal:** Preparar y probar KPI, Compras, IA y operación antes del arranque real.

**Architecture:** Proyectos separados sobre modelos, servicios y permisos nativos de Odoo.
La auditoría instalada determina qué se reutiliza; cada incremento tendrá su propio
diseño y plan de implementación. No crear interfaces ficticias ni fijar datos reales por inferencia.

**Tech Stack:** Odoo19/Python/PostgreSQL, vistas/Owl cuando proceda, SSH manual del usuario para verificaciones instaladas.

**Spec:** docs/superpowers/specs/2026-11-03-preparacion-uso-real-design.md

## Global Constraints

- Producción19.0.25.6.0/main40ce2fe permanece como baseline; no activar políticas reales.
- STAGING/copia aislada y datos ficticios para desarrollo/ensayos. No reutilizar la copia QA cerrada.
- No enviar comunicaciones/pedidos reales, contratar proveedores/modelos ni asumir identidades.
- KPI autorizados por empresa/origen; privados y valores desconocidos no se convierten en cero.
- Compras y factura comercial son ámbitos distintos; Defontana/SII fuera de este programa.

## Review Focus

1. KPI con cancelaciones, cierres manuales históricos, reprogramación, zonas horarias y datos faltantes.
2. Lecturas agregadas que filtren datos o amplíen acceso a empresas/historial privado.
3. Compra aprobada frente a recibido, parciales, devoluciones y stock disponible.
4. Cuenta compartida frente a empleado e identidad del agente; acciones duplicadas por reintentos.
5. Datos ficticios confundidos con reales y activaciones/correcciones irreversibles antes del arranque.

### Task1: Auditar la instalación sin modificarla

**Files:**
- Create: `.tmp/preparacion-uso-real-pilot/source.py` (workspace Code, fuera del módulo).
- Create: `.tmp/staging-preparacion-uso-real-source.ps1` y payload/hash/recibo local.
- Update: `docs/pendientes.md` con alcance actual y estado de auditoría.

**Interfaces:** Consume baseline137 de la entrega verificada y registro de módulos/campos.
Produce JSON versionado con `readonly`, `rolled_back`, modelos/campos, módulos,
fuentes seleccionadas, permisos nativos y estadísticas agregadas; sin secretos ni datos individuales.

- [x] Escribir el colector con READ ONLY, rechazo de BD distinta y rollback en finally.
- [x] Preparar transporte/hash/verificador que rechace error SSH, marcadores ausentes,
  informe inválido o ausencia de rollback. No declarar consulta ejecutada al construir el paquete.
- [x] Comprobar sintaxis y límites locales: dos respuestas válidas y 13 rechazos del verificador real.
- [x] Ejecutar solo mediante SSH privado del usuario.
- [x] Validar recibo20261103-162622-901:33 modelos, READ ONLY/rollback,137 fuentes y PID intactos.

### Task2: Especificar y entregar el primer incremento de KPI

- [x] Mapear cada indicador a campos/hitos realmente disponibles y fijar población,
  plazo original/vigente, cobertura, fechas/filtros y evidencia accesible por rol.
- [x] Escribir diseño y plan específicos con archivos, interfaces y pruebas exactas.
- [x] TDD: fórmulas y permisos;16 cálculos puros y36 contratos nativos en GREEN.
- [x] Investigación2026-11-04 de reportes Odoo19, KPI típicos y giro ROV, con cobertura
  y brechas de datos. Regresión del servicio1282/1282 aprobada en STAGING.
- [x] Contrastar propuesta externa y consolidar22 familias,11 fichas iniciales,
  D1 y paneles operativos; revisión independiente aplicada. Catálogo:
  `docs/superpowers/specs/2026-11-04-kpi-catalogo-consolidado.md`.
- [x] Preparar auditoría complementaria de fuentes/cobertura agregada antes de
  proponer campos nuevos; comprobaciones locales del paquete aprobadas.
- [x] Auditoría complementaria READ ONLY mediante SSH privado: recibo20261104-115911-124
  revalidado,34 modelos/139 fuentes/PID intactos. Mapa actualizado; revisión Q1–Q4
  distingue captura existente e historia faltante, sin inferir rendimiento desde QA.
- [x] F3: regla de promesa en Odoo al aceptar trabajo y fecha, original/cambios con
  motivo/autor, comparación con salida validada y sin compromiso cuando falta fecha,
  aceptada2026-11-04. Documento/vínculo/roles y captura concreta siguen pendientes.
- [x] Q2: ventana180 días desde salida del taller elegida2026-11-04, independiente
  de garantía; separar tasa de cohortes maduras y retornos/visitas aún en seguimiento.
  Enlace técnico, cobertura y casos de borde siguen pendientes de especificación.
- [x] Q1: observaciones informativas sin corrección/reensayo pendiente cuentan
  como primer pase si cumplen todas las pruebas obligatorias. Liberación exige
  pruebas aprobadas, documentación completa y cero NC bloqueantes pendientes.
- [x] F2: causas iniciales de detención aceptadas; intervalos reales y unión de
  tiempos. Duración por causa no aditiva propuesta sin reparto arbitrario.
- [x] Calendario del tablero aceptado: Santiago, semanas lunes–domingo y meses/años
  calendario. Se conservan calendarios operativos para plazos laborales.
- [x] Primer núcleo empresarial local Q1/Q2/liberación:34 pruebas nuevas y16 anteriores,
  revisión independiente corregida en RED/GREEN,50/50 unitarias y pylint10/Black99.
  Plan: `docs/superpowers/plans/2026-11-04-business-kpi-quality-foundation.md`.
- [ ] Consultar perfiles/chequeos/puntos de calidad instalados antes de ampliar captura;
  paquete READ ONLY preparado, aún no ejecutado; no usar semillas como perfiles vigentes.
- [ ] Acordar con el usuario el catálogo empresarial y las fichas de medida antes
  de continuar el tablero; el primer servicio de etapas fue propuesta de Codex.
- [ ] Tablero y navegación autorizada; pruebas de interfaz/ambos temas/roles y revisión independiente.
- [ ] Integración y entrega concretas; no usar datos QA para metas de rendimiento reales.

### Task3: Diseñar y entregar Compras/abastecimiento

- [ ] Usar auditoría para diseñar el circuito nativo y las conexiones que falten.
- [ ] Resolver responsables/umbrales antes de configuraciones reales.
- [ ] Plan específico por incrementos; comprobar solicitud/cotización/aprobación/orden,
  recepción parcial/restante/devolución y vínculo con necesidades del taller.
- [ ] QA aislado, permisos/empresas, revisión y entrega sin generar pedidos reales.

### Task4: Diseñar y entregar el agente IA

- [ ] Confirmar funciones nativas/licencia, acciones permitidas y proveedor/coste antes de contratar.
- [ ] Plan específico: primero consultas/resúmenes; después acciones autorizadas e identidad auditada.
- [ ] Pruebas de permisos, identidad Odoo/Telegram, reintentos, datos restringidos y confirmación de acciones.
- [ ] Credenciales privadas aportadas por el usuario cuando el diseño las necesite; ningún secreto en evidencia.

### Task5: Preparar datos, personas y operación

- [ ] Informe de faltantes de datos maestros y propuesta de carga reconciliada.
- [ ] Matriz de roles/personas/cuentas y pruebas de permisos con usuarios equivalentes.
- [ ] Procedimientos/capacitación por recorrido y excepciones.
- [ ] Verificar respaldos/recuperación, monitoreo y notificaciones con evidencia actual.

### Task6: Ensayo general y arranque

- [ ] Especificar casos y criterios de aceptación con los componentes ya entregados.
- [ ] Ensayar en entorno aislado con datos ficticios, incluyendo fallo/recuperación.
- [ ] Preparar carga inicial, corte y políticas concretas con responsables y calendarios reales.
- [ ] Presentar el arranque listo para revisar; ejecutar activación explícita y comprobar los primeros casos reales.

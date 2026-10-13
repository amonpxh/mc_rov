# Trabajo asignado manual — plan de implementación

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking. Ejecución directa aprobada por el usuario el 2026-10-09. Primera entrega instalada en STAGING 19.0.24.5.0: 415/415 GREEN y HOOT18/18. Exportación focalizada 1/1 aprobada; QA visual con roles reales pendiente.

**Goal:** El jefe puede repartir actividades entre empleados que usan cuentas compartidas y consultarlas desde el Centro, ligadas a sus registros reales.

**Architecture:** Extender actividades nativas con asignación de empleado y añadir accesos personales/de equipo al Centro. Reutilizar acciones y vistas nativas; separar el servicio de asignaciones de los dominios ROV del servicio operativo existente. No crear tareas espejo ni automatizaciones en esta primera entrega.

**Tech Stack:** Odoo 19 Enterprise, ORM Python, XML, OWL, pruebas TransactionCase y HOOT.

**Spec:** [Trabajo asignado](../specs/2026-10-09-trabajo-asignado-design.md).

## Global Constraints

- Usuario asignado es cuenta; Empleado asignado es ejecutor. Ninguno acredita autor humano.
- Mi trabajo filtra la cuenta conectada; empleado es un filtro, no identidad ni permiso.
- Trabajo del equipo y coordinación son permisos distintos; validar también en servidor.
- Mantener accesos por proceso actuales, reportes PDF, confirmaciones y estados operativos.
- Pendientes manuales pueden ser no ROV y de otros módulos, dentro de permisos/empresas.
- No importar la lista de ejemplos, crear actividades históricas, entregar equipos ni mover materiales.
- Tareas/Proyectos siguen con asignación nativa por usuario en esta fase; no fingir asignación por empleado.
- No crear actividades automáticas todavía; segunda entrega con plan propio tras este piloto.
- Sonda de STAGING de solo lectura; instalar únicamente mediante runner con respaldo/restauración.

## Review Focus

1. Cuenta Taller compartida: dos empleados diferenciados sin modificar responsable de REV.
2. Cable/no ROV y compra: inclusión por autorización, no por categoría ROV.
3. Actividad asignada con origen inaccesible: no filtrar nombre del documento ni abrirlo.
4. Una selección múltiple contiene un registro prohibido: no reasignar parcialmente los demás.
5. Trabajo terminado con entrega incierta/reingreso: ninguna acción sobre actividad altera cierre, stock o visita anterior.

Cada caso se prueba en las tareas indicadas abajo. No se prueban automatizaciones mediante esta entrega manual.

## Archivos e interfaces

- Crear `models/mail_activity.py`: extensión de actividad y validación de empleado/empresa.
- Crear `models/mc_rov_work_assignment.py`: acciones y validaciones del trabajo asignado.
- Crear `models/mc_rov_activity_assignment_wizard.py`: reasignación individual/múltiple.
- Crear `security/work_assignment_groups.xml`: consulta equipo y coordinación independientes.
- Crear `views/mail_activity_views.xml` y `views/mc_rov_activity_assignment_wizard_views.xml`.
- Modificar `models/__init__.py`, `__manifest__.py`, `security/ir.model.access.csv`.
- Modificar `static/src/work_center/work_center.js`, `.xml`, `.scss` para entrada y selectores.
- Crear `tests/test_work_assignment.py`; modificar `tests/__init__.py` y `static/tests/work_center.test.js`.
- Mantener `models/mc_rov_work_center.py` para sus seis áreas: no ampliar su dominio ROV a tareas.

Contrato del servicio `mc.rov.work.assignment`:

```python
get_capabilities()  # {"can_view_team": bool, "can_coordinate": bool}
action_activities(scope="mine", employee_id=False, user_id=False)
action_tasks(scope="mine")
action_projects(scope="mine")
action_assign(activity_ids)  # abre wizard tras validar todos los registros
action_open_source(activity_id)  # comprueba acceso al origen; acción exacta
```

Las acciones devuelven diccionarios act_window nativos. scopes válidos: mine/team;
rechazar valores ajenos y llamadas team sin permiso. Employee_id es ID validado por
consulta pública, no nombre ni lista privada de RRHH. No usar IDs de acciones de
STAGING en código; resolver XML IDs auditados. Nuevas acciones conservan filtros y
empresa activa, pero incluyen futuras; no heredar Vencidas/Hoy de acción 124.

## Tarea 1: comprobar contratos instalados antes de escribir producto

**Files:** crear `.tmp/staging-work-assignment-source.ps1` y `.tmp/work-assignment-source/probe.sh`, evidencia fuera del repo publicable.

- [x] Leer fuentes instaladas de `mail.activity`, vistas/lista/Kanban, planificador,
  `hr.employee`/`hr.employee.public`, `project.task` y selección de empleados.
- [x] Consultar campos, acciones y permisos de purchase.order, stock.picking, sale.order,
  res.partner, documentos y CRM si están instalados. No prometer soporte si faltan.
- [x] Confirmar campo/referencia pública del empleado y selección segura sin conceder
  RRHH privado; probar la lectura con usuario no HR mediante entorno de lectura.
- [x] Confirmar metadatos/ciclo de actividad y acceso al origen; rollback, sin datos QA.
- [x] Guardar diagnóstico y ajustar solo interfaces técnicas del plan si difiere la
  fuente instalada. Si exige ampliar permisos o cambiar el diseño, volver a revisión.

**Verificación:** shell `bash -n`, parser PowerShell y AST Python; respuesta tiene
rollback=True, versión/archivos y permisos consultados. No continuar con supuestos
sobre nombres privados o XML IDs. Esta tarea entrega evidencia de lectura, no instala.

## Tarea 2: asignación de empleado segura

**Files:** `models/mail_activity.py`, registros/imports, grupos y `tests/test_work_assignment.py`.

- [x] Escribir tests: cuenta compartida con dos empleados, empleado vacío, empleado
  activo/inactivo, dos empresas, nombre privado no accesible, fecha/usuario nativos.
- [x] RED focalizado en STAGING contra modelo instalado, usando pruebas temporales restaurables.
- [x] Añadir `mc_employee_id` como referencia al empleado; no exigir login ni copiar
  responsable del origen. Selección/nombre públicos según contrato de Tarea 1.
- [x] Rechazar nueva asignación de empleado archivado o incompatible con empresa;
  conservar referencias anteriores al archivado. Empresa efectiva se obtiene del origen.
- [x] Probar GREEN y consulta de nombres sin HR privado; no alterar mail.activity ajenas.

Ejemplo del contrato que debe fijar el test (fixtures creadas con rollback):

```python
activity.write({"user_id": taller.id, "mc_employee_id": pedro.id})
self.assertEqual(activity.user_id, taller)
self.assertEqual(activity.mc_employee_id, pedro)
self.assertEqual(revision.responsable_id, original_revision_employee)
```

**Commit propuesto:** `feat: asignar empleado a actividades sin confundir cuenta y técnico`.

## Tarea 3: consulta personal y equipo sin exposición de registros

**Files:** `models/mc_rov_work_assignment.py`, `security/work_assignment_groups.xml`, imports, tests.

- [x] Tests RED: mine devuelve cuenta propia; team requiere grupo; usuario de otra
  compañía; empleado ajeno; no ROV incluido; tareas personales y proyectos con acceso.
- [x] Tests RED: actividad legible por asignación pero documento inaccesible; la
  consulta del Centro excluye información del origen y action_open_source falla.
- [x] Implementar contratos anteriores sin sudo. La vista/acción debe aplicar la
  misma restricción de origen que el servicio; filtrar en el Centro no protege una
  acción nativa directa. Resolver mediante dominio validado y reglas aplicables,
  con pruebas de llamada directa de lectura, no solo del botón.
- [x] Consultar capacidades en servidor; no inferir Supervisor por nombre.
- [x] Para tareas/proyectos, usar acceso nativo y usuario actual en mine; team necesita
  grupo de consulta más permisos nativos. No inventar dueño del proyecto por creador.
- [x] GREEN focalizado. Probar fuente válida abre registro exacto y no busca «último».

Ejemplo de test de frontera:

```python
with self.assertRaises(AccessError):
    service.with_user(taller).action_activities(scope="team")
with self.assertRaises(AccessError):
    service.with_user(taller).action_open_source(inaccessible_activity.id)
```

**Commit propuesto:** `feat: consultar trabajo personal y de equipo con permisos de origen`.

## Tarea 4: repartir y reprogramar trabajo desde una lista

**Files:** wizard, vistas, ACL e imports, extensión de vista actividad, tests.

- [x] Tests RED: coordinación sin consulta global; consulta sin coordinación; seleccionar
  varias actividades con una prohibida; no hay escrituras parciales; cambios de fecha
  requieren motivo cuando reprograman una fecha existente.
- [x] Implementar wizard con usuario, empleado y fecha, cada uno con opción explícita
  de aplicar cambio. Distinguir «no modificar empleado» de «quitar empleado».
- [x] Validar todo el conjunto antes de escribir, en una transacción; sin elevación.
  Registrar reasignación/reprogramación en documento con cuenta autora, motivo y datos
  permitidos. No atribuir al empleado asignado autoría de la escritura.
- [x] Añadir entrada al wizard desde selección de actividades; grupos controlan acción
  y backend. Apertura individual/múltiple usa `action_assign(activity_ids)`.
- [x] GREEN: empleado de próxima acción no se copia desde técnico que hizo avance previo;
  completing/reassigning activity no modifica entrega, stock, revisión ni otra visita.

```python
before = allowed_activity.user_id
with self.assertRaises(AccessError):
    coordinator.action_assign([allowed_activity.id, forbidden_activity.id])
self.assertEqual(allowed_activity.user_id, before)
```

**Commit propuesto:** `feat: repartir actividades y registrar reprogramación del trabajo`.

## Tarea 5: acceso desde Centro y pruebas frontend

**Files:** assets WorkCenter y `static/tests/work_center.test.js`.

- [x] HOOT RED: entrada Trabajo asignado, mine/team condicionado, filtro empleado,
  futuras incluidas, Tareas/Proyectos abren acción correcta, retorno conserva filtros.
- [x] Añadir sección compacta sin sustituir las seis áreas. Actividades abre vistas
  nativas lista/Kanban/calendario extendidas; no montar otro tablero de tarjetas.
- [x] Vista sin empleado muestra «Sin empleado asignado»; nombre restringido no se
  expone. No sumar tareas/proyectos/actividades como un contador de trabajo único.
- [x] No mostrar filtro empleado sobre tareas que aún no tienen campo de asignación.
- [x] HOOT GREEN 18/18.
- [ ] QA visual de cuenta compartida: Pedro/Ana se filtran desde Taller; actividad
  sobre cable visible; cambio de filtro no cambia permisos ni responsables de registros.

```javascript
expect(capturedAction.res_model).toBe("mail.activity");
expect(capturedAction.context.allowed_company_ids).toEqual([companyId]);
```

**Commit propuesto:** `feat: abrir trabajo asignado desde el Centro de trabajo`.

## Tarea 6: cerrar la primera entrega manual

- [x] Lint/hooks y suite focalizada tras cada cambio; suite mc_rov completa al cerrar
  backend, HOOT al cerrar frontend. Repetir solo por cambios/fallos pertinentes.
- [ ] QA manual Supervisor/Taller/Dev con privilegios reales; fixtures revertidas y
  verificaciones negativas de lectura/edición. No crear ejemplos de clientes como QA.
- [x] Comparar hashes QWeb, estados y conteos operativos; no cambiar PDFs.
- [ ] Actualizar versión, diseño/pendientes y evidencia, revisar diff, PR/CI y aprobación
  visual de STAGING antes de preparar despliegue a producción.
- [ ] Preparar un plan independiente para la regla automática solo tras validar este
  reparto manual. Ninguna configuración/fecha automática se activa con esta entrega.

## Autorrevisión y estado

Se cubren los cinco focos en tareas 2–5. Fuentes instaladas y selección pública son
prerrequisitos verificables de tarea 1. Fuentes recuperadas y tarea 2 validada en
STAGING (6/6). Tarea 3: ocho contratos RED confirmados; servicio instalado,
GREEN remoto de 14 contratos aprobado. Tarea 4: ocho tests RED confirmados;
asistente y accion nativa instalados; GREEN de 22 contratos aprobado en STAGING. No se creó trabajo real. Automatización, empleado en project.task,
vínculos operativos de tareas y actividades propias de REV/FEN quedan fuera de esta
primera entrega y requieren planes separados. Las entradas nuevas de trabajo no
arrastran filtro ROV, mientras las seis áreas actuales conservan su alcance vigente.

Verificación final de STAGING:415/415, sin fallos/errores (2026-10-09 18:47:50).
Privacidad de consultas, agrupación, lectura nativa y auditoría validada; respaldo
PA4bdI. Exportación usa etiqueta pública segura; la prueba focalizada 1/1 pasó a las
19:10 UTC, incluyendo permiso nativo y protección del origen. Las cuentas reales Taller/Dev/Supervisor no se crearon como fixtures de
navegador: su QA de uso permanece pendiente; contratos de permisos sí ejecutados.

## Integración visual aprobada: ejecución en curso

1. Fuentes Odoo 19 instaladas auditadas; filtro cruzado implementado y 38 contratos GREEN en STAGING.
2. Seis pruebas de contenedor RED confirmadas en HOOT.
3. Implementación local de host y puente `AssignedWorkView`, aislamiento de callbacks/configuración y protección antes de cambiar sección. Sintaxis verificada.
4. Pendiente instalar assets con `staging-work-assignment-embedded-frontend-green.ps1`, ejecutar 27 pruebas HOOT y comprobar vistas nativas reales (menús, búsqueda, creación, navegación/retorno, scroll).
5. Resolver cualquier fallo, revisar diff, añadir tests de proceso al módulo, validar suite final cuando corresponda y actualizar PR #102. Sin merge/PROD antes de QA aprobada.

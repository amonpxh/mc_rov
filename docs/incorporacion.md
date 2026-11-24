# Incorporación a mc_rov

## Primer día

1. Solicita acceso al repositorio privado con tu cuenta de GitHub. Acuerda con Paulo el primer alcance, quién te revisa y si necesitarás un entorno Odoo 19 Enterprise. Para revisar documentación y ejecutar el cálculo puro de KPI basta el clon y el entorno Python descrito en el runbook de pruebas. Reserva staging y producción para los responsables autorizados.
2. Clona el repositorio, consulta `origin/main`, revisa `git status --short` y `git worktree list`. Usa una rama y un checkout propios. Si una tarea depende de un PR abierto, acuerda esa base y deja constancia de la dependencia.
3. Lee [AGENTS.md](../AGENTS.md), el [estado vigente](pendientes.md) y el [flujo de Git](agents/git-flow.md). Usa luego el diseño y las pruebas del área que vas a tocar.
4. Aporta evidencia del commit que revisas. En la [plantilla del PR](../.github/PULL_REQUEST_TEMPLATE.md) explica el problema, resultado, pruebas, efectos sobre datos y permisos y límites. Paulo autoriza el squash del HEAD revisado. Despliegue y activación se autorizan aparte.

## Dónde buscar el contexto

| Pregunta | Fuentes |
| --- | --- |
| ¿Qué reglas de código y negocio debo preservar? | [Instrucciones compartidas](../AGENTS.md) y [reglas del dominio y sus motivos](agents/dominio.md). |
| ¿Por qué existe este flujo? | [Diseños ROV](designs/), [especificaciones](superpowers/specs/), [planes y evidencia técnica](superpowers/plans/). Para una decisión histórica, contrasta diseño, PR integrado, código y pruebas. |
| ¿Cómo se mide y qué falta? | [Catálogo KPI](superpowers/specs/2026-11-04-kpi-catalogo-consolidado.md), [pendientes vigentes](pendientes.md) y [aceptación operativa](runbooks/aceptacion-operativa-rov.md). |
| ¿Cómo pruebo y entrego? | [Pruebas](runbooks/testing.md), [Staging y QA](runbooks/staging.md), [versionado](agents/releases.md) y [despliegue](runbooks/deploy.md). |
| ¿Qué cambió y cuándo? | [CHANGELOG](../CHANGELOG.md) y PR correspondientes. Una versión identifica código. Consulta el estado vigente para confirmar una instalación. |

## Revisión entre dos personas

Acordar un revisor distinto del autor y pedirle revisar el diff, los resultados de CI del HEAD exacto y los cambios de permisos, datos, migraciones o recuperación. Para cambios de comportamiento, incluir la reproducción y la regresión. Una nueva revisión del HEAD es necesaria si cambia algo material. Verifica la configuración efectiva en GitHub: la aprobación explícita y el CI actual forman parte del acuerdo del equipo. Consulta con Paulo las cuentas con escritura elegibles para CODEOWNERS y quién revisa seguridad y migraciones; la configuración de propietarios no sustituye la autorización de merge.

## Inicio de sesión para el asistente de IA

Abre el agente en el checkout de la tarea y dale esta instrucción, incluyendo al final el objetivo concreto:

> Lee AGENTS.md, el resumen vigente de docs/pendientes.md y docs/agents/git-flow.md. Confirma rama y worktree. Consulta el diseño y las pruebas de mi tarea. Indica la evidencia que permite distinguir cambios locales, PR, integración, instalación y activación. Trabaja solo en el alcance autorizado. Si repo, PR y notas se contradicen, contrástalos antes de tocar código o entornos.

El repositorio conserva decisiones, casos reproducibles y referencias a evidencia. Credenciales, respaldos, filestores y registros privados se gestionan por los canales autorizados del equipo. La incorporación requiere acceso GitHub y, cuando corresponda, cuentas de un entorno de pruebas con el rol adecuado.

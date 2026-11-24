# mc_rov — Marine Connection

Módulo de Odoo 19 Enterprise para diseñar, fabricar, reparar y mantener ROVs. Integra series, revisiones, pruebas, fichas PDF, Calidad, Ingeniería, Inventario, Centro de trabajo y KPI operativos.

- [Incorporación al equipo](docs/incorporacion.md) · Ruta de lectura, acceso, primer PR y contexto para asistentes de IA.
- [Instrucciones del repositorio](AGENTS.md) · Reglas compartidas por personas y agentes. [Claude Code](CLAUDE.md) importa el mismo archivo.
- [Estado vigente y pendientes](docs/pendientes.md) · Qué está integrado, instalado, en ensayo o pendiente.
- [Flujo Git y revisión](docs/agents/git-flow.md) · [Versionado](docs/agents/releases.md) · [Historial de cambios](CHANGELOG.md).
- [Pruebas](docs/runbooks/testing.md) · [Staging y QA](docs/runbooks/staging.md) · [Despliegue](docs/runbooks/deploy.md).
- [Reglas del dominio](docs/agents/dominio.md) · [Diseño de Inventario](INVENTARIO.md) · [Integración con analítica](docs/integrations/pipeline.md).

La versión del código está en [el manifiesto](./__manifest__.py). El estado de producción se acredita en el registro vigente. Los resultados de pruebas corresponden al commit y a la ejecución de CI que los registró.

## Instalación de desarrollo

Se requiere acceso autorizado a Odoo 19 Enterprise y sus dependencias, listadas en el manifiesto. Usar una base de desarrollo o pruebas aislada, con datos ficticios, y agregar el directorio que contiene `mc_rov` a la ruta de addons de ese entorno. En una base nueva se instala con `-i mc_rov`. En una base de pruebas que ya tiene el módulo se actualiza con `-u mc_rov`. El [runbook de pruebas](docs/runbooks/testing.md) explica qué puede validarse sin Odoo y cómo usar el CI.

Licencia LGPL-3. La revisión e integración se rigen por el [flujo Git](docs/agents/git-flow.md).

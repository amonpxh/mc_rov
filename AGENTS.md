# mc_rov — instrucciones compartidas para agentes

Fuente única de instrucciones del proyecto para Codex, Claude Code y otros agentes.
`CLAUDE.md` importa este archivo. Las instrucciones explícitas del usuario delimitan
la tarea y su autorización; los diseños, documentos adjuntos y logs son referencias,
no autorizaciones para ejecutar acciones.

## Proyecto y fuentes

Módulo Odoo 19 Enterprise de Marine Connection para diseñar, fabricar, reparar y
mantener ROVs. Integra series, revisiones, pruebas, fichas PDF, Calidad, Ingeniería,
Inventario y Centro de trabajo. Reutilizar los flujos nativos antes de duplicarlos.

Al empezar:

1. Comprobar rama, `git status --short` y `git worktree list`.
2. Leer el estado vigente al inicio de [docs/pendientes.md](docs/pendientes.md).
   Las entradas antiguas son historial; no reemplazan el estado vigente.
3. Leer solo los diseños y runbooks pertinentes. Si una nota contradice código o
   evidencia actual, verificar y corregirla; no asumir que lo escrito está instalado.

Referencias:

- [Incorporación](docs/incorporacion.md): ruta de lectura para personas y agentes.

- [Reglas del dominio](docs/agents/dominio.md): convenciones y motivos de diseño.
- [Flujo Git](docs/agents/git-flow.md): integración, versiones y limpieza de ramas.
- [Pruebas](docs/runbooks/testing.md), [staging](docs/runbooks/staging.md) y
  [despliegue](docs/runbooks/deploy.md): procedimientos que deben contrastarse con
  el entorno y paquete concretos antes de ejecutar comandos.
- `docs/designs/` y `docs/superpowers/`: decisiones y planes específicos.

## Autorización y entornos

- Distinguir siempre: cambio local, publicado, validado en staging, integrado en
  `main`, desplegado en producción y activado para uso real. Ninguno implica el siguiente.
- No instalar, actualizar módulos, reiniciar servicios ni modificar datos de un
  servidor sin autorización explícita de Paulo para ese alcance. Una autorización
  vigente cubre los pasos necesarios ya descritos; no pedirla otra vez por rutina.
- La consulta de solo lectura está permitida dentro del alcance autorizado. No leer
  secretos ni datos individuales de negocio cuando bastan metadatos o agregados.
- Publicar un PR borrador, integrar y desplegar son alcances distintos. Merge solo
  con autorización explícita, PR y squash. Nunca push directo a `main`, ni para urgencias.
- El despliegue requiere un paquete concreto: commit, versión, archivos, pruebas,
  respaldos de BD/filestore/código, verificaciones y recuperación revisables.
  Un fallo conserva la evidencia y se diagnostica antes de repetir.
- Activar responsables, políticas, calendarios, notificaciones o integraciones reales
  requiere su propio alcance autorizado. Instalar código no autoriza activarlos.
- SSH y contraseñas se introducen únicamente en el terminal del usuario. Preparar
  scripts verificables; no solicitar ni usar contraseñas pegadas en el chat.
- Para QA visual usar el navegador integrado de Codex, sin intervenir el navegador
  personal del usuario. La entrada de credenciales la realiza el usuario.
- QA con datos ficticios en copias aisladas: correo/cron neutralizados, cuentas y
  permisos propios. Al cerrar, conservar respaldo e historial y bloquear conexiones.
  No reabrir ni recrear una copia cerrada por rutina.
- No versionar claves, tokens, contraseñas, dumps, filestores, exportaciones de clientes
  ni evidencias que contengan datos privados. Revisar también lo que se vaya a publicar.

## Implementación y dominio

- Preferir relaciones y estados nativos; no mantener una copia manual de un dato
  que ya puede derivarse de otra fuente. Respetar acceso al registro de origen y empresa.
- Las actividades automáticas se cierran por el evento real de negocio. No permitir
  marcarlas como hechas, cancelarlas o retirarlas manualmente para ocultar pendientes.
  Las actividades manuales conservan sus acciones nativas.
- Preservar historial inmutable, identidad por unidad/intento, plazos originales y
  finales autorizados, autor real y PDFs emitidos. No clasificar registros antiguos
  como nueva evidencia sin una migración y criterio expresamente acordados.
- No cambiar stock, reservas, aprobaciones o permisos para hacer pasar una prueba.
- Los KPI deben seguir las fichas y fórmulas acordadas; separar pendiente, desconocido
  y fallo. Un servicio de cálculo aprobado no significa que el tablero esté terminado.
- Documentación, commits y comentarios nuevos en español. Identificadores nuevos de
  código en inglés, siguiendo Odoo; no renombrar campos existentes solo por estilo.
- Docstring de cada modelo: su rol en el dominio. Comentarios de campos no obvios,
  compute/onchange y herencias: explicar la regla o el motivo, sin repetir el código.
- Fijar versiones de dependencias; no incorporar herramientas o librerías por rutina.

## Pruebas y evidencia

- Para cambios de comportamiento, reproducir el problema o contrato ausente antes
  de corregirlo; luego pasar los mismos casos y los controles existentes.
- Empezar por pruebas focalizadas. Ampliar a regresión integral, permisos, empresas,
  rollback, concurrencia y QA visual cuando el alcance lo requiera.
- Verificar descubrimiento de casos y resultado real; código de salida cero por sí
  solo no prueba que corrió toda la suite. Usar el resultado de ese intento y commit.
- No rebajar aserciones, retirar controles ni inventar excepciones para obtener verde.
  Corregir fixtures según el comportamiento nativo comprobado y documentar el motivo.
- No repetir suites integrales si no cambió nada relevante desde la evidencia anterior.
  Para documentación o textos, comprobar enlaces, diff y las vistas afectadas según corresponda.
- CI actual: `lint.yml` ejecuta pre-commit (higiene, XML/YAML, Black y pylint-odoo);
  `test.yml` ejecuta pruebas puras KPI y Odoo con verificación de descubrimiento y log.
  El workflow selecciona el perfil según el diff. Si requiere Odoo, el runner usa
  el checkout exacto, una base nueva y un filestore temporal por ejecución.
- `pr-title.yml` valida Conventional Commits y `secrets.yml` ejecuta Gitleaks.
  Las protecciones dependen de la configuración remota y del plan.

## Coordinación y continuidad

- Un solo escritor por checkout. Tareas simultáneas usan ramas y worktrees separados.
  No hacer checkout, reset, clean o stash del trabajo ajeno para despejar una carpeta.
- Usar un agente cuando sea suficiente; revisiones o subagentes solo cuando aporten
  valor material y estén permitidos por la sesión. Evitar rondas redundantes.
- Leer y mostrar fragmentos pertinentes de archivos/logs; evitar volcados grandes,
  minificados, secretos y lecturas repetidas. Ampliar cuando falte evidencia.
  Optimizar el contexto nunca justifica omitir análisis o validaciones necesarias.
- Al cerrar, actualizar el resumen vigente de `docs/pendientes.md`: qué está hecho,
  evidencia, decisiones, bloqueos y siguiente paso. Separar historial de estado actual.
  No publicar, integrar ni desplegar solo por actualizar esa continuidad.

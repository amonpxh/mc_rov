# Cola de CI y callbacks de ramas históricas

## Fallos reproducidos

- Los Tests de PR116 y PR117 fueron cancelados mientras esperaban el runner aunque
  `cancel-in-progress` estaba en false. GitHub mantiene por defecto solo una ejecución
  pendiente por grupo: una entrada nueva sustituye a la pendiente anterior.
- Run42832103314 falló en el callback de un PR anterior al motor de versionado:
  el job verify hizo checkout del SHA histórico y ejecutó unittest sin casos.
  El runtime devuelve código5 para «NO TESTS RAN». No falló Odoo ni hubo escrituras.

## Corrección

- `queue: max` conserva hasta100 ejecuciones pendientes en Tests y versionado,
  manteniendo una sola ejecución activa por grupo y sin cancelar la que ya corre.
  No se paralelizan procesos que comparten `odoo_test`.
- Los callbacks de ramas distintas de main omiten todo el flujo de versionado.
  Los PR actuales siguen probando su propio HEAD, sin permisos de escritura.
- En un callback de main, verify prueba el motor de la definición vigente; el job
  de propuesta conserva el checkout del SHA del evento para verificar su entrega real.
  Si ese SHA es anterior al motor, se omite su paso de publicación.
- Se conservan el filtro de repositorio, CI por SHA, controles de identidad,
  lease de ramas, releases borrador y separación del despliegue.
- Se completa checkout7.0.1 también en este workflow nuevo, que no existía cuando
  Dependabot abrió PR117. SHA oficial verificado y runtime del runner compatible.

Validación: YAML y hooks,38 contratos del motor/bot; CI del PR. Después de integrar,
comprobar un callback de Dependabot antiguo (jobs omitidos) y uno de main anterior
al motor (verify vigente aprobado y publicación omitida). No rebajar los controles
ni dar por exitosa una suite con cero casos.

[Cola oficial de GitHub](https://docs.github.com/en/actions/how-tos/write-workflows/choose-when-workflows-run/control-workflow-concurrency).

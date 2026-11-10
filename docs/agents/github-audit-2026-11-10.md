# Auditoría de GitHub — 10 de noviembre de 2026

Repositorio privado: `amonpxh/mc_rov`. Consulta por API; la consulta inicial no cambió configuración ni ramas.
La ejecución posterior autorizada se registra al final de este documento. Inventario válido para los SHA indicados;
revalidar antes de cualquier limpieza.

## Estado comprobado

- `main`: `dea4efb05c9ca911c24e37b61b60c6da86270cdc`, PR #114 integrado con squash.
- CI posterior al merge: Lint `42682761910` y Tests `42682762063`, ambos completados
  con `success`. Esto no acredita instalación en producción.
- 54 ramas remotas: `main` y 53 antiguas. No hay PR abiertos en la consulta.
- 52 ramas antiguas coinciden exactamente con el HEAD registrado de un PR integrado.
  Una, `fix/el-origen-en-un-solo-lugar`, corresponde al PR #81 cerrado sin integrar.
- Tres de las 52 integradas siguen vinculadas a worktrees locales. Se pospone su
  limpieza hasta revisar su contenido; quedan 49 candidatas remotas iniciales.
- Checkout principal local en `439d013` con cambios del usuario; no se actualizó,
  cambió de rama ni limpió. No usar ese checkout como prueba del estado remoto actual.
- `delete_branch_on_merge=false`; squash, merge commit y rebase están permitidos.
- `main` figura sin protección. API de rulesets responde 403 y solicita GitHub Pro
  o repositorio público. Mantener privado; confirmar plan compatible para protecciones.
- Existen workflows de pruebas y lint, pre-commit y `CODEOWNERS` en la raíz.
  No había Dependabot, plantilla de PR, control de título ni escáner de secretos.

## Cambios locales preparados en esta rama

- `AGENTS.md` concentra instrucciones y enlaza reglas del dominio sin perderlas.
  `CLAUDE.md` solo lo importa; se elimina la referencia circular.
- Flujo documentado sin `develop`, push directo ni despliegue implícito tras merge.
- Lint apunta solo a `main` y declara `contents: read`.
- Plantilla de PR y Dependabot semanal para GitHub Actions. No se agregó ecosistema
  pip porque no hay un manifiesto de dependencias pip en esta entrega. Las revisiones
  de pre-commit no quedan cubiertas por ese bloque de Dependabot.
- Estos archivos requieren publicación e integración para aplicarse en GitHub.
  No se cambió código de producto, versión ni infraestructura del runner.

## Ajustes remotos recomendados, pendientes de aplicar

1. Habilitar borrado automático de ramas fusionadas y dejar solo squash como método
   de integración. No habilitar auto-merge: conservar autorización explícita.
2. Limpiar las 49 candidatas después de revalidar SHA y conservar este inventario.
   Resolver aparte las tres con worktrees y la rama del PR #81.
3. En un plan compatible con repositorios privados, proteger `main`: exigir PR y
   los dos checks actuales, bloquear force-push y borrado, y exigir conversaciones
   resueltas. Revisiones obligatorias solo si hay otro revisor humano disponible;
   no establecer una aprobación que el único mantenedor no puede otorgarse.
4. Agregar validación de título Conventional Commits en un workflow seguro y un
   escáner de secretos. Auditar primero el historial: cualquier secreto real se rota,
   no se silencia con una exclusión. Revisar permisos y procedencia del escáner.
5. Fijar las acciones a SHA completo revisado y mantenerlas con Dependabot; hoy usan
   tags versionados. Revisar por separado actualizaciones de hooks de pre-commit.
6. Auditar aislamiento y permisos del runner self-hosted antes de aceptar código
   externo: el checkout aislado protege fuentes operativas, pero no equivale a
   aislamiento del host. No ejecutar PR no confiables junto a recursos productivos.
7. Preparar tags/releases por entrega y registrar commit realmente instalado,
   respaldo y comprobación posterior. No desplegar automáticamente por merge.

Fuentes oficiales:

- [Borrado automático de ramas](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/configuring-pull-request-merges/managing-the-automatic-deletion-of-branches).
- [Protecciones y disponibilidad por plan](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-protected-branches/about-protected-branches).

## Inventario para revisión, no orden de borrado

| Rama | PR | SHA observado | Tratamiento propuesto |
|---|---|---|---|
| `docs/auditoria-fabricacion-calidad` | #97 | `274a5df0d385` | Eliminada; respaldo Git verificado |
| `docs/carga-sin-required` | #42 | `0d9471fe6510` | Eliminada; respaldo Git verificado |
| `docs/cierre-aviso-produccion` | #91 | `792d0bead873` | Eliminada; respaldo Git verificado |
| `docs/cierre-diseno-fabricacion` | #47 | `34fc3f611874` | Eliminada; respaldo Git verificado |
| `docs/cierre-fen-navigation` | #96 | `4cc17a8498c9` | Eliminada; respaldo Git verificado |
| `docs/cierre-navegacion-revisiones` | #93 | `85437b834ece` | Eliminada; respaldo Git verificado |
| `docs/cierre-produccion-028af90` | #89 | `3245c599c72d` | Eliminada; respaldo Git verificado |
| `docs/cierre-quality-navigation` | #99 | `b2fd61c3a013` | Eliminada; respaldo Git verificado |
| `docs/diseno-fabricacion` | #44 | `db3af03d7a70` | Eliminada; respaldo Git verificado |
| `docs/fabricacion-verificado` | #43 | `51c76df79f36` | Eliminada; respaldo Git verificado |
| `docs/lo-que-faltaba` | #48 | `f00adcb839d5` | Eliminada; respaldo Git verificado |
| `docs/ordenar-pendientes` | #94 | `81d56887083a` | Eliminada; respaldo Git verificado |
| `docs/protocolo-analisis-y-reporte` | #18 | `9ea6233c7fb6` | Eliminada; respaldo Git verificado |
| `docs/staging` | #45 | `a3c97580b5cc` | Eliminada; respaldo Git verificado |
| `feature/acceptance-quality-activities` | #108 | `99f45fb11e7a` | Revisar worktree y continuidad local antes de limpiar |
| `feature/bateria-accesorios` | #35 | `ba6797adbdaf` | Eliminada; respaldo Git verificado |
| `feature/bateria-por-area` | #34 | `9991e374af40` | Eliminada; respaldo Git verificado |
| `feature/catalogos-y-protocolo-primero` | #21 | `b118c870da91` | Eliminada; respaldo Git verificado |
| `feature/centro-responsables-icono` | #101 | `48c5b38bebcc` | Eliminada; respaldo Git verificado |
| `feature/centro-trabajo-rov` | #100 | `02d416f07b65` | Eliminada; respaldo Git verificado |
| `feature/design-inventory-activities` | #112 | `f6b8a5c98b9a` | Eliminada; respaldo Git verificado |
| `feature/diagnostico-de-fallas` | #30 | `0118a1e97802` | Eliminada; respaldo Git verificado |
| `feature/fen-navigation` | #95 | `9acdeb0754df` | Eliminada; respaldo Git verificado |
| `feature/fichas-pdf` | #84 | `2c4234b94c07` | Eliminada; respaldo Git verificado |
| `feature/flujo-por-momentos` | #31 | `80d114f0e1a1` | Eliminada; respaldo Git verificado |
| `feature/guia-reparacion` | #90 | `1b3d7dd73c97` | Eliminada; respaldo Git verificado |
| `feature/imprimir-ficha-desde-orden` | #85 | `ae4933322fa2` | Eliminada; respaldo Git verificado |
| `feature/inspeccion-de-sellos` | #22 | `db7d4d10928f` | Eliminada; respaldo Git verificado |
| `feature/inventory-activities` | #113 | `1def0f2407fe` | Eliminada; respaldo Git verificado |
| `feature/manufacturing-activities` | #106 | `5409fefd8ec7` | Eliminada; respaldo Git verificado |
| `feature/navegacion-revisiones` | #92 | `bf78abcf5758` | Eliminada; respaldo Git verificado |
| `feature/preparacion-uso-real` | #114 | `6a346ba7fa99` | Revisar worktree y continuidad local antes de limpiar |
| `feature/protocolo-implementacion` | #20 | `dcee920971fd` | Eliminada; respaldo Git verificado |
| `feature/quality-production-navigation` | #98 | `6ec300663afd` | Eliminada; respaldo Git verificado |
| `feature/renombre-revision-tecnica` | #23 | `c810b9f003bd` | Eliminada; respaldo Git verificado |
| `feature/repair-activities` | #103 | `0f15342d222e` | Eliminada; respaldo Git verificado |
| `feature/software-en-la-bateria` | #39 | `33c3fb34e25a` | Eliminada; respaldo Git verificado |
| `feature/trabajo-asignado-manual` | #102 | `cf949fb6f035` | Revisar worktree y continuidad local antes de limpiar |
| `feature/ultima-ficha-espaciado-botones` | #86 | `d94977b3b22f` | Eliminada; respaldo Git verificado |
| `feature/work-center-inventory` | #109 | `4ab521d3f3da` | Eliminada; respaldo Git verificado |
| `feature/work-center-inventory-workspace` | #110 | `d6e15edc65b7` | Eliminada; respaldo Git verificado |
| `fix/boton-revision-fabricacion` | #24 | `1033f1c8ab8f` | Eliminada; respaldo Git verificado |
| `fix/buscar-la-prueba` | #33 | `413b6edb140c` | Eliminada; respaldo Git verificado |
| `fix/cabecera-y-nombre-de-acro` | #41 | `f29f21b3039f` | Eliminada; respaldo Git verificado |
| `fix/el-origen-en-un-solo-lugar` | #81 | `7f8d3f281173` | Conservar: cerrado sin integrar; revisar contenido |
| `fix/nombres-de-linea` | #32 | `8f05a907dacc` | Eliminada; respaldo Git verificado |
| `fix/orden-de-la-bateria` | #36 | `3e94ef7a2d36` | Eliminada; respaldo Git verificado |
| `fix/orden-y-columnas-del-checklist` | #40 | `528508a65288` | Eliminada; respaldo Git verificado |
| `fix/pantalla-de-la-revision` | #38 | `a0cf07f55347` | Eliminada; respaldo Git verificado |
| `fix/rev-letter-footer-y-acciones-rov` | #88 | `0a9302e6538d` | Eliminada; respaldo Git verificado |
| `fix/runbook-staging-permisos` | #46 | `1981483f3922` | Eliminada; respaldo Git verificado |
| `fix/work-center-design-icon` | #111 | `72b231d966f7` | Eliminada; respaldo Git verificado |
| `refactor/una-corrida-por-revision` | #37 | `3feb47874e49` | Eliminada; respaldo Git verificado |


## Ejecución autorizada — 10 de noviembre de 2026

- Reconsulta: squash exclusivo y borrado automático YA habilitados por el usuario;
  auto-merge desactivado. No fue necesario cambiar esos ajustes.
- Eliminadas 49 referencias remotas mediante push atómico con leases para cada SHA.
  Inventario completo y bundle verificado guardados fuera del repositorio en
  `.tmp/github-governance-audit/`; también se conservaron referencias locales de respaldo.
  No se borró ningún worktree ni archivo local.
- Reconsulta posterior: exactamente cinco ramas, con SHA intactos: main,
  feature/acceptance-quality-activities, feature/preparacion-uso-real,
  feature/trabajo-asignado-manual y fix/el-origen-en-un-solo-lugar.
- Protección de main: API sigue devolviendo 403 por plan privado no compatible.
  Tener permisos admin no elimina esa restricción; no se cambió visibilidad ni plan.
- Preparados workflows de título Conventional Commits y Gitleaks en runners de GitHub,
  con permisos de solo lectura. No usan pull_request_target ni ejecutan títulos como shell.
- Acciones existentes fijadas a SHA resuelto desde las versiones oficiales. Gitleaks
  8.30.1 fijado a archivo oficial y checksum SHA256; descarga verificada.
- Escaneo local de todo el historial alcanzable, incluidas referencias de respaldo:
  338 commits, cero hallazgos; salida redactada. No se subió informe privado.
- Sin tags ni releases preexistentes en la consulta. Las entregas necesitan identidad
  de código y un registro separado del despliegue; ver releases.md.
- Los archivos nuevos siguen sin integrar en main. CI del PR debe validarlos antes
  de considerar instalados los controles. El runner Odoo no cambió de infraestructura.


## Cierre de limpieza y decisión de plan gratuito

Por autorización posterior del usuario se revisaron y eliminaron las cuatro refs
conservadas. Tres tenían cambios locales: se guardaron parches y se verificaron los
diffs/status intactos después del borrado remoto. PR81 ya estaba representado en la
vista vigente y en su sección de CHANGELOG; su ref también quedó en bundle verificado.
Total: 53 ramas antiguas borradas. Los worktrees y ramas locales se conservan.

La rama del PR115 se eliminó automáticamente al integrarlo. Las tres ramas nuevas de
Dependabot corresponden a PR116/117/118 abiertos y no se borran. La nueva rama de
versionado también es trabajo activo. No contratar Pro/Team: el usuario excluyó
protecciones de pago y previews 3D. Las recomendaciones anteriores que dependían
del plan quedan descartadas para este alcance, no como bloqueo pendiente.

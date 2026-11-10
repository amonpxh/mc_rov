# GitHub Flow, integración y entrega

## Flujo

`main` → rama de tarea → PR borrador → revisión y pruebas → squash autorizado →
CI de `main` → paquete y despliegue autorizados → activación acordada, si corresponde.

- Sin `develop`. `main` es la línea integrada y desplegable; puede estar por delante
  de producción. No representa por sí sola la versión instalada.
- Crear cada tarea desde `origin/main` recién consultado. Si el checkout contiene
  trabajo pendiente, usar otro worktree; no cambiar la rama de una carpeta compartida.
- Una rama por tarea coherente, corta cuando sea posible. Para programas extensos,
  entregar incrementos revisables; no imponer un plazo ficticio de uno a tres días.
- Prefijos: `feature/`, `fix/`, `refactor/`, `data/`, `docs/`, `test/`, `ci/`, `chore/`.
- Abrir PR borrador cuando esté autorizada su publicación. Describir problema,
  resultado, validación, límites y cambios de datos/permisos; usar la plantilla.
- Antes del merge: comprobar HEAD exacto, diff, CI actual, conflictos y pruebas de
  staging pertinentes. Revisar formato, Odoo, Gitleaks y Conventional Commits;
  en la entrega del versionado se agrega `Pruebas de versionado`.
- Paulo revisa y autoriza la integración. Un agente puede ejecutarla cuando la haya
  autorizado explícitamente. Usar squash y volver a comprobar commit/CI de `main`.
- Nada de push directo, force-push a `main` o excepción para un hotfix pequeño.
  No fusionar cambios nuevos bajo la autorización de un HEAD anterior sin revisarlos.
- Merge no inicia un despliegue. Preparar la entrega y obtener la autorización
  correspondiente antes de modificar producción. Registrar commit instalado y evidencia.

## Commits y versiones

Título recomendado de PR y commit final:
`tipo(alcance opcional): descripción breve en español`.

Tipos: `feat`, `fix`, `perf`, `refactor`, `docs`, `test`, `ci`, `chore`, `style`, `data`.
Usar `!` y explicar migración/compatibilidad si el cambio rompe datos o contratos.
El workflow `pr-title.yml` agregado en esta rama valida el formato en eventos de PR,
incluidos cambios de título. Confirmar su CI e integración antes de considerarlo activo.

El manifiesto usa `19.0.X.Y.Z`: `19.0` identifica Odoo; `X` cambios incompatibles,
`Y` funciones compatibles y `Z` correcciones compatibles. Los números existentes
se conservan. Evaluar migraciones según esquema y datos, no solo según la etiqueta:
una recomputación de datos puede necesitar migración aunque sea compatible.

- Cada entrega de producto debe tener una versión nueva revisada antes de actualizar
  el módulo; agrupar incrementos en una entrega es válido si el paquete los identifica.
- No subir versión del módulo por documentación o configuración de CI sin cambio de producto.
- Un tag `v19.0.X.Y.Z` identifica código de una entrega, no demuestra que se instaló.
  Registrar aparte el despliegue efectivo. No mover un tag publicado ni crear etiquetas
  retroactivas de instalación sin evidencia del commit realmente instalado.
- El workflow de versionado propone una entrega como PR borrador y, una vez integrada
  la entrega con CI aprobado, prepara una release borrador. No publica tags ni instala
  Odoo. Publicar la release y desplegar son pasos explícitos y separados.

## GitHub gratuito

El usuario decidió mantener el repositorio privado en el plan gratuito. No queda
pendiente contratar Pro/Team, hacer público el código ni habilitar previews 3D.
Los agentes comprueban PR, HEAD y CI antes de cada merge autorizado; sin protección
de pago, GitHub no impide técnicamente que alguien con escritura omita ese acuerdo.

Squash exclusivo y borrado automático sí están habilitados. Dependabot propone
actualizaciones, pero no se integran por rutina: revisar compatibilidad del runner,
permisos y CI, especialmente en cambios mayores de acciones.

## Limpieza de ramas

El borrado automático de ramas fusionadas es una opción de GitHub, no una regla que
un Markdown active. Revisar su valor real antes de anunciarlo como habilitado.

Para la limpieza histórica:

1. Registrar rama, SHA actual, PR, estado y SHA de HEAD integrado.
2. Excluir `main`, PR abiertos, ramas sin PR integrado y ramas con commits posteriores.
3. Revisar worktrees locales, archivos modificados y dependencias entre tareas.
   Que un PR esté integrado no autoriza borrar su carpeta ni cambios posteriores.
4. Conservar un inventario recuperable y borrar solo las referencias aprobadas.
5. Después, `fetch --prune` limpia referencias remotas locales. No borra ramas locales.
   Retirar un worktree solo si está limpio y su trabajo quedó preservado.

Con squash, `git branch --merged main` no identifica por sí solo todas las ramas
integradas: el commit final tiene otra identidad. Tampoco basta con que coincida el
nombre de rama; comprobar el SHA del HEAD del PR. No usar `branch -D` como limpieza masiva.

## Controles de GitHub

Consultar [registro de entregas](releases.md) y [auditoría y propuestas](github-audit-2026-11-10.md) para el estado observado.
Las recomendaciones de configuración no deben confundirse con controles ya aplicados.

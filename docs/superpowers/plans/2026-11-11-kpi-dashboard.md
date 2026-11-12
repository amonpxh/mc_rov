# Plan de implementación: primer tablero KPI autorizado

> Ejecución inline con `superpowers:executing-plans`; pruebas primero y revisión
> independiente de la entrega al final. Diseño aprobado, no pedir aprobación otra vez.

**Objetivo:** entrada Indicadores en Centro, con cartera actual, primera aceptación,
seguimiento de seis procesos y cobertura de las once fichas, sin inventar datos.
**Especificación:** `../specs/2026-11-11-tablero-kpi-design.md`.
**Arquitectura:** puente Odoo de solo lectura que selecciona población completa
autorizada y delega cálculos existentes; componente OWL independiente. Catálogo de
cobertura separado de números. Sin tablas, ACL privadas ni dependencias nuevas.

## Restricciones comunes

- Base local origin/main97c9348; producto25.7.0/36e0f37 instalado en producción.
- No tocar producción o QA cerrada, ni conceder roles o activar políticas reales.
- Sin filtro temporal sobre Q1: las selecciones actuales incluyen órdenes cerradas
  y archivadas, no páginas de veinte. Seis flujos de etapas no son unidades producidas.
- Conservar permiso de equipo/origen/empresas. Error de historial impide ese Q1;
  nunca quitar el fracaso inaccesible para mejorar denominador.
- Fuente de cartera y acciones con dominios nativos; no usar sudo sobre orígenes.
- Servicios existentes son contratos: no cambiar sus fórmulas para simplificar UI.

## Revisión de riesgos

Paginación que cambia denominador; fallo histórico ocultado por estado/permiso;
empresa/contexto falsificado; filtros temporales que aparentan cohorte Q1;
consulta o detalle que escribe, abre privados o muestra datos de otro origen.

### Task 1: contrato nativo del puente de lectura

**Crear:** `tests/test_kpi_dashboard.py`, `models/kpi_dashboard.py`.
**Modificar:** `tests/__init__.py`, `models/__init__.py`.
**Interfaz propuesta:** `mc.rov.kpi.dashboard.get_dashboard(date_from=False,
date_to=False, process='all')` retorna `portfolio`, `quality`, `tracking`, `coverage`;
`action_detail(key)` acepta solo cartera repair/manufacturing y selección Q1
repair/manufacturing. Métodos auxiliares privados para seleccionar fuente completa.

- [x] Escribir contratos ausentes y controles nativos; primer intento en STAGING.
- [x] Diagnosticar fixture que interrumpía sin fallo real y corregir su preparación.
- [x] Usuario autoriza publicar rama y PR borrador para continuar automáticamente por CI.
- [ ] Observar RED exacto del intento real; errores de fixtures no son RED válido.
- [x] Implementar puente READ ONLY delegando Q1/seguimiento; no devolver `episodes`
      ni IDs de intentos privados, solamente resúmenes y acciones autorizadas.
- [ ] Verificar GREEN focalizado con nombres exactos y datos/fuentes intactos.

### Task 2: vista nativa y presentación

**Crear:** `static/src/kpi_dashboard/kpi_dashboard.js`, `.xml`, `.scss` y helper de
presentación puro; `views/kpi_dashboard_views.xml`; pruebas HOOT y puras apropiadas.
**Modificar:** assets/data del manifiesto, registro de pruebas según convenciones.
**Consumir:** respuesta de Task1; ORM y action Odoo. Guardar pestaña/filtros al volver.

- [x] Pruebas antes de código: Sin base, desconocido, sin acceso, empresa cambiada,
      error RPC, respuesta tardía y navegación al detalle/vuelta.
- [x] Resumen/Calidad/Seguimiento/Cobertura; filtros de cierre solo en Seguimiento.
- [x] Menú para grupo de consulta del equipo sin nuevas membresías.
- [ ] RED/GREEN de vistas y HOOT, escritorio/móvil en navegador integrado.

### Task 3: revisión y entrega del primer incremento

- [ ] Permisos, empresas, lectura sin escrituras, sin fuga de privados o episodios.
- [x] Revisión independiente del conjunto; corregir fallos con regresiones.
- [ ] Regresión integral sobre producto final una vez; UI y QA aislado donde corresponda.
- [ ] Documentar evidencia, actualizar pendientes y preparar publicación solo cuando
      se autorice. Integración y producción no se infieren de este desarrollo.

## Continuación de las otras fichas

Decisión de ejecución2026-11-11: usar CI existente (`odoo_test`, checkout aislado)
para los siguientes RED/GREEN sin SSH del usuario. No modificar workflows ni
probar contra producción. El PR borrador estará rojo intencionalmente hasta
implementar el contrato y se verificará el log completo por nombre de caso.

Después del primer incremento: F4/F5/Q4 con vínculos/fechas comprobados; después
F2/F3/F6 y cartera histórica; después Q2/Q3/A1 según captura. Esto no declara
implementadas las once familias por mostrar sus fichas. Los planes concretos se
fijan contra código y auditorías existentes antes de la captura correspondiente.

# Pruebas de mc_rov

## Validación desde el clon

Desde la raíz, ejecutar los controles que correspondan al cambio. `pre-commit run --all-files` usa las versiones fijadas en [la configuración](../../.pre-commit-config.yaml).

```bash
PYTHONPATH=models python3 -m unittest discover -s tests/unit -v
```

```powershell
$env:PYTHONPATH = 'models'
python -m unittest discover -s tests/unit -v
```

El cálculo usa Python estándar y requiere la zona IANA `America/Santiago`. En Windows, si no está disponible, instala `tzdata==2025.2` con `python -m pip install tzdata==2025.2` en tu entorno de desarrollo. Para documentación, comprobar `git diff --check`, los enlaces y los ejemplos afectados. Consultar [AGENTS.md](../../AGENTS.md) para el criterio de regresión.

## Prueba focalizada en Odoo

Requiere Odoo 19 Enterprise, el addon resuelto desde el checkout de prueba y una base de pruebas propia que ya tenga instalado el módulo. Verificar rutas y base antes de usar el ejemplo en Linux. Para una instalación inicial en una base nueva se usa `-i`.

```bash
odoo -c "$ODOO_TEST_CONFIG" -d "$ODOO_TEST_DB" -u mc_rov \
  --test-tags /mc_rov:TestStockLotRov --stop-after-init --no-http --max-cron-threads 0
```

Verificar que el log enumere las clases y métodos esperados y termine con cero fallos y errores. Un selector incorrecto puede devolver salida exitosa sin descubrir casos.

## CI del repositorio

El [workflow de Odoo](../../.github/workflows/test.yml) clasifica el diff del commit exacto.

| Perfil | Qué ejecuta |
| --- | --- |
| Documentación | Valida enlaces locales agregados y los controles de formato, título, Gitleaks y versionado. |
| Cambios en pruebas puras | Ejecuta la suite de pruebas puras de KPI. |
| Fórmula de Trabajo asignado en un PR | Ejecuta las pruebas puras y el grupo nativo `work_kpi`. |
| Cambios compartidos, de alcance incierto o de producto integrados en main | Ejecuta pruebas puras, contratos focalizados, carreras, navegador, HOOT y la regresión nativa. |

Cuando corresponde Odoo, el [script del runner](../../scripts/ci/run_odoo_tests.sh) verifica el addon del checkout. La ejecución instala el módulo en una base nueva, usa un filestore temporal y conserva logs y el recibo del ciclo de la base. Las carreras se ejecutan en una copia derivada. El control agregado **Odoo module tests** confirma el resultado del perfil que corresponde al cambio. En documentación, es normal que **Odoo en base efímera** aparezca omitido.

- Abrir los controles del PR y comprobar el SHA, el resultado y el recuento de casos de esa ejecución. Usar el artefacto `odoo-tests` para contrastar el log y los casos específicos.
- Revisar también formato, título, Gitleaks y versionado según [el flujo Git](../agents/git-flow.md). El acuerdo del equipo exige controles verdes antes del merge autorizado. Comprobar aparte la protección efectiva de GitHub.
- Para comprobar que un rol comprende y puede completar el trabajo en Odoo, usar el [ensayo de aceptación con usuarios](aceptacion-operativa-rov.md).

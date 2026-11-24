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

El [workflow de Odoo](../../.github/workflows/test.yml) usa el commit exacto en un checkout aislado y la base dedicada `odoo_test` del runner. Ejecuta pruebas puras y [el script del runner](../../scripts/ci/run_odoo_tests.sh). Ese script verifica la resolución del addon, corre contratos focalizados, carreras y recorridos en una copia de la base de pruebas, navegador y HOOT, y la regresión nativa con verificación de descubrimiento. El ejemplo focalizado de arriba cubre solo contratos nativos.

- Abrir los controles del PR y comprobar el SHA, el resultado y el recuento de casos de esa ejecución. Usar el artefacto `odoo-tests` para contrastar el log y los casos específicos.
- Revisar también formato, título, Gitleaks y versionado según [el flujo Git](../agents/git-flow.md). El acuerdo del equipo exige controles verdes antes del merge autorizado. Comprobar aparte la protección efectiva de GitHub.
- Para comprobar que un rol comprende y puede completar el trabajo en Odoo, usar el [ensayo de aceptación con usuarios](aceptacion-operativa-rov.md).

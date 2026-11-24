#!/usr/bin/env bash
set -euo pipefail

REPO=$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd -P)
test "$(basename "$REPO")" = mc_rov
case "$REPO" in
    /opt/odoo/custom-addons/*|/opt/odoo/staging-addons/*)
        echo 'Refusing to run CI from an operational checkout' >&2
        exit 1
        ;;
esac
PROFILE=${1:?}
DATABASE=${MC_ROV_CI_DATABASE:?}
DATA_DIR=${MC_ROV_CI_DATA_DIR:?}
[[ "$DATABASE" =~ ^mc_rov_ci_[a-f0-9]{32}$ ]]
test -d "$DATA_DIR"
test "$PROFILE" = full || test "$PROFILE" = work_kpi
CONF=/etc/odoo/odoo.conf
ADDONS=$(python3 - "$REPO" "$CONF" <<'PY'
import configparser
import sys
from pathlib import Path
repo = Path(sys.argv[1]).resolve()
config = configparser.ConfigParser(interpolation=None)
assert config.read(sys.argv[2]), 'Odoo config not readable'
paths = [str(repo.parent)]
paths.extend(item.strip() for item in config.get('options', 'addons_path').split(',') if item.strip())
print(','.join(dict.fromkeys(paths)))
PY
)

# Verify Odoo's actual module resolution before connecting to the test database.
python3 - "$REPO" "$CONF" "$ADDONS" <<'PY'
import sys
from pathlib import Path
from odoo.tools import config
from odoo.modules.module import get_module_path, initialize_sys_path
config.parse_config(['-c', sys.argv[2], '--addons-path', sys.argv[3]])
initialize_sys_path()
resolved = get_module_path('mc_rov')
assert resolved and Path(resolved).resolve() == Path(sys.argv[1]).resolve(), resolved
print('CI_ODOO_SOURCE=' + resolved)
PY

COMMON=(-d "$DATABASE" --data-dir "$DATA_DIR" --config "$CONF" --addons-path "$ADDONS"
    --stop-after-init --no-http --http-port 8199 --gevent-port 8198 --workers 0
    --max-cron-threads 0 --db-filter "^$DATABASE$" --logfile '')

INSTALL_LOG=$(mktemp "${RUNNER_TEMP:?}/mc-rov-tests.install.XXXXXX.log")
odoo "${COMMON[@]}" -i mc_rov,project --without-demo --load-language=es_CL 2>&1 | tee "$INSTALL_LOG"

LOG=$(mktemp "${RUNNER_TEMP:?}/mc-rov-tests.XXXXXX.log")
if test "$PROFILE" = work_kpi; then
    TAGS=work_kpi
else
    FOCUSED_LOG=$(mktemp "${RUNNER_TEMP:?}/mc-rov-tests.production-focus.XXXXXX.log")
    # Estas rutas usan Proyecto, una salida nativa y el asistente de informes.
    BASELINE_TAGS=production_kpi_capture
    for method in \
        TestWorkAssignmentProcess.test_tarea_sin_vinculo_no_hereda_proceso_por_titulo \
        TestCustomerCommitmentRepairDispatch.test_native_outgoing_needs_a_linked_physical_evidence \
        TestReporteFicha.test_asistente_selecciona_documento_y_opciones \
        TestReporteFicha.test_orden_propone_la_ultima_revision_y_permite_escoger_otra; do
        BASELINE_TAGS="$BASELINE_TAGS,/mc_rov:$method"
    done
    odoo "${COMMON[@]}" -u mc_rov --test-tags "$BASELINE_TAGS" --log-level test \
        2>&1 | tee "$FOCUSED_LOG"
    python3 "$REPO/scripts/ci/run_production_kpi_races.py" "$REPO" "$CONF" "$ADDONS"
    python3 "$REPO/scripts/ci/run_kpi_browser_tests.py" "$REPO" "$CONF" "$ADDONS"
    TAGS=/mc_rov,-kpi_dashboard_browser
fi
odoo "${COMMON[@]}" -u mc_rov --test-tags "$TAGS" --log-level test 2>&1 | tee "$LOG"

# A successful process with missing tests is not a successful suite.
python3 - "$REPO/tests" "$LOG" "$PROFILE" <<'PY'
import ast
import re
import sys
from pathlib import Path
tests = Path(sys.argv[1])
expected = set()
modules = re.findall(r'^from \. import (\w+)', (tests / '__init__.py').read_text(), re.M)
for module in (['test_work_kpi'] if sys.argv[3] == 'work_kpi' else modules):
    # Los HttpCase se verifican aparte con HTTP local y navegador real, nunca por skip.
    if module in {'test_kpi_dashboard_browser', 'test_customer_commitment_browser', 'test_repair_lead_time_browser', 'test_repair_return_browser'}:
        continue
    tree = ast.parse((tests / (module + '.py')).read_text(encoding='utf-8'))
    for cls in tree.body:
        if isinstance(cls, ast.ClassDef):
            expected.update((cls.name, method.name) for method in cls.body
                if isinstance(method, ast.FunctionDef) and method.name.startswith('test_'))
text = Path(sys.argv[2]).read_text(encoding='utf-8')
summary = re.findall(r'(\d+) failed, (\d+) error\(s\) of (\d+) tests', text)
assert summary and int(summary[-1][0]) == int(summary[-1][1]) == 0, summary
observed = re.findall(r'Starting (\w+)\.(test_\w+)', text)
assert expected and not (expected - set(observed)), sorted(expected - set(observed))
assert int(summary[-1][2]) == len(observed) >= len(expected)
print('CI_ODOO_DISCOVERY=PASSED EXPECTED=%s ACTUAL=%s' % (len(expected), len(observed)))
PY

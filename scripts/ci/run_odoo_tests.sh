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

LOG=$(mktemp "${RUNNER_TEMP:?}/mc-rov-tests.XXXXXX.log")
# Solo capacidad existente: no instalar navegador ni modificar el host para comprobarla.
if command -v google-chrome >/dev/null || command -v chromium >/dev/null || command -v chromium-browser >/dev/null; then
    echo CI_BROWSER_AVAILABLE=True
else
    echo CI_BROWSER_AVAILABLE=False
fi
odoo -d odoo_test -u mc_rov --test-tags /mc_rov --stop-after-init --no-http \
    --http-port 8199 --gevent-port 8198 --workers 0 --max-cron-threads 0 \
    --db-filter '^odoo_test$' --log-level test --logfile '' \
    --config "$CONF" --addons-path "$ADDONS" 2>&1 | tee "$LOG"

# A successful process with missing tests is not a successful suite.
python3 - "$REPO/tests" "$LOG" <<'PY'
import ast
import re
import sys
from pathlib import Path
tests = Path(sys.argv[1])
expected = set()
for module in re.findall(r'^from \. import (\w+)', (tests / '__init__.py').read_text(), re.M):
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

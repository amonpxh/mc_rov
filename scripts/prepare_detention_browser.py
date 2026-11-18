"""Congela navegador y regresión integral sobre el candidato F2 aprobado."""

import argparse
import json
from pathlib import Path

from prepare_detention_interface_green import overlay
from prepare_detention_red import ROOT, sha


def _verified_candidate(source):
    """Vincula el candidato, su evidencia de ejecución y la revocación."""
    manifest = json.loads((source / "prepared.json").read_text())
    receipt = json.loads((source / "verified-result.json").read_text())
    assert manifest["phase"] == "interface-green" and receipt["passed"]
    assert receipt["access_revoked"] and (receipt["tests"], receipt["races"]) == (
        69,
        10,
    )
    for name, digest in receipt["evidence"].items():
        assert sha((source / "temporary-access" / name).read_bytes()) == digest
    for name, digest in manifest["files"].items():
        assert sha((source / name).read_bytes()) == digest
    assert manifest["files"]["source.tar"] == receipt["source_sha256"]
    return manifest, receipt["source_sha256"]


def prepare(source, output):
    """Reutiliza los guardas del GREEN y deja HTTP dentro de la red privada."""
    manifest, source_hash = _verified_candidate(source)
    files = {
        name: (source / name).read_bytes()
        for name in manifest["files"]
        if name.startswith("test_")
        or name
        in (
            "source.tar",
            "observed-source.json",
            "baseline.json",
            "check_baseline.py",
        )
    }
    test = "tests/test_kpi_dashboard_browser.py"
    files["source.tar"] = overlay(
        files["source.tar"], {test: (ROOT / test).read_bytes().replace(b"\r\n", b"\n")}
    )
    for relative in (
        "scripts/ci/run_kpi_browser_tests.py",
        "scripts/qa/detention_browser.py",
    ):
        path = Path(relative)
        files[path.name] = (ROOT / path).read_bytes().replace(b"\r\n", b"\n")
    ci = (ROOT / "scripts/ci/run_odoo_tests.sh").read_text()
    _, marker, discovery = ci.partition('python3 - "$REPO/tests" "$LOG" <<\'PY\'\n')
    assert marker and discovery.endswith("\nPY\n")
    files["verify_regression.py"] = discovery.removesuffix("PY\n").encode()
    files["run.sh"] = _browser_runner((source / "run.sh").read_text()).encode()
    assert output.name == "kpi-detentions-browser"
    output.mkdir(exist_ok=False)
    for name, content in files.items():
        (output / name).write_bytes(content)
    manifest.update(
        phase="interface-browser",
        tests=7,
        races=0,
        files={name: sha(content) for name, content in files.items()},
        green_source_sha256=source_hash,
    )
    (output / "prepared.json").write_text(json.dumps(manifest, indent=2) + "\n")


def _browser_runner(original):
    """Conserva la preparación, la comparación de fuentes y el cierre del clúster."""
    begin = original.index(
        "echo DETENTION_INTERFACE_GREEN_PHASE=upgrade-isolated-copy-and-native-contracts"
    )
    end = original.index('python3 "$PAYLOAD/check_baseline.py"', begin)
    runner = original[:begin] + BROWSER_AND_REGRESSION + original[end:]
    return runner.replace("DETENTION_INTERFACE_GREEN", "DETENTION_BROWSER")


BROWSER_AND_REGRESSION = """echo DETENTION_BROWSER_PHASE=prepare-pinned-browser
for file in detention_browser.py run_kpi_browser_tests.py; do
    install -o odoo -g odoo -m 600 "$PAYLOAD/$file" "$WORK/evidence/$file"
done
runuser -u odoo -- timeout 240s python3 "$WORK/evidence/detention_browser.py" prepare "$WORK" "$DB"
echo DETENTION_BROWSER_PHASE=loopback-browser-and-hoot
set +e
unshare --net -- bash -c '
    set -e
    ip link set lo up
    exec runuser -u odoo -- timeout --signal=TERM --kill-after=20s 1140s python3 "$1/evidence/detention_browser.py" run "$1" "$2"
' _ "$WORK" "$DB"
BROWSER_RC=$?
set -e
echo "DETENTION_BROWSER_BROWSER_RC=$BROWSER_RC"
if test -f "$WORK/evidence/browser.log"; then
    cp "$WORK/evidence/browser.log" "$WORK/tests.log"
fi
test "$BROWSER_RC" = 0
echo DETENTION_BROWSER_PHASE=full-native-regression
set +e
unshare --net -- runuser -u odoo -- timeout --signal=TERM --kill-after=20s 1500s \\
    odoo -c "$WORK/isolated.conf" -d "$DB" -u mc_rov --test-tags /mc_rov,-kpi_dashboard_browser \\
    --db-filter "^$DB$" --stop-after-init --no-http --workers 0 --max-cron-threads 0 \\
    --log-level test --logfile "$WORK/evidence/regression.log" > "$WORK/regression-console.log" 2>&1
REGRESSION_RC=$?
set -e
echo "DETENTION_BROWSER_REGRESSION_RC=$REGRESSION_RC"
if test -f "$WORK/evidence/regression.log"; then
    # Conserva el log completo en la copia. Transporta descubrimiento y fallos.
    awk '/Starting |failed, .*error[(]s[)] of |FAIL:|ERROR:| CRITICAL /' \\
        "$WORK/evidence/regression.log" >> "$WORK/tests.log"
fi
test "$REGRESSION_RC" = 0
python3 "$PAYLOAD/verify_regression.py" "$WORK/addons/mc_rov/tests" "$WORK/evidence/regression.log"
"""


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("output", type=Path)
    options = parser.parse_args()
    prepare(options.source, options.output)

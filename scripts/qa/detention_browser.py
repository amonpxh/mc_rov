"""Prepara Chrome verificado y valida navegador dentro de la copia F2."""

import json
import os
from pathlib import Path
import re
import socket
import subprocess
import sys

from run_kpi_browser_tests import browser_environment, prepare_browser, verify_result


def main(mode, work, database):
    """Limita Odoo y Chrome al clúster y directorio privados previstos."""
    assert re.fullmatch(r"/var/tmp/mc-rov-detention-races-[A-Za-z0-9]{6}", str(work))
    assert database == "mc_rov_detention_races_" + work.name.rsplit("-", 1)[1]
    tools = work / "evidence/browser"
    if mode == "prepare":
        tools.mkdir()
        environment = browser_environment(tools, prepare_browser(tools))
        (tools / "environment.json").write_text(
            json.dumps({key: environment[key] for key in ("PYTHONPATH", "ODOO_BROWSER_BIN")})
        )
        return
    assert mode == "run" and {name for _, name in socket.if_nameindex()} == {"lo"}
    repo = work / "addons/mc_rov"
    expected_hoot = sum(
        len(re.findall(r"^\s*test\(", path.read_text(encoding="utf-8"), re.M))
        for path in (repo / "static/tests").glob("*.test.js")
    )
    environment = json.loads((tools / "environment.json").read_text())
    log = work / "evidence/browser.log"
    with log.open("w") as output:
        result = subprocess.run(
            [
                "odoo",
                "-c",
                str(work / "isolated.conf"),
                "-d",
                database,
                "-u",
                "mc_rov",
                "--test-tags",
                "/mc_rov:TestKPIDashboardBrowser",
                "--stop-after-init",
                "--http-interface",
                "127.0.0.1",
                "--http-port",
                "8199",
                "--gevent-port",
                "8198",
                "--workers",
                "0",
                "--max-cron-threads",
                "0",
                "--db-filter",
                "^" + database + "$",
                "--log-level",
                "test",
                "--logfile",
                "",
            ],
            env={**os.environ, **environment},
            stdout=output,
            stderr=subprocess.STDOUT,
            timeout=1100,
            check=False,
        )
    verify_result(log.read_text(encoding="utf-8"), result.returncode, expected_hoot)


if __name__ == "__main__":
    main(sys.argv[1], Path(sys.argv[2]), sys.argv[3])

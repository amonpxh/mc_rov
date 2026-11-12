"""Ejecuta Chrome temporal y HttpCase sobre odoo_test, sin instalar paquetes del host."""

import hashlib
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import urllib.request
import zipfile


VERSION = "157.0.8103.78"
ARCHIVE_URL = (
    "https://storage.googleapis.com/chrome-for-testing-public/"
    f"{VERSION}/linux64/chrome-headless-shell-linux64.zip"
)
SHA256 = "f90329720fb61e5a76da9b6b509b6ad12a484c9c5df0359403e935177c6d153a"


def prepare_browser(root):
    archive = root / "browser.zip"
    digest = hashlib.sha256()
    with urllib.request.urlopen(ARCHIVE_URL, timeout=60) as response, archive.open("wb") as output:
        while chunk := response.read(1024 * 1024):
            digest.update(chunk)
            output.write(chunk)
    if digest.hexdigest() != SHA256:
        raise RuntimeError("La huella del navegador no coincide con la versión revisada")
    with zipfile.ZipFile(archive) as package:
        for member in package.infolist():
            if not (root / member.filename).resolve().is_relative_to(root):
                raise RuntimeError("Ruta inválida en el navegador descargado")
        package.extractall(root)
    executable = root / "chrome-headless-shell-linux64" / "chrome-headless-shell"
    executable.chmod(0o700)
    subprocess.run([str(executable), "--version"], check=True, timeout=15)
    print("CI_BROWSER_VERSION=" + VERSION, flush=True)
    print("CI_BROWSER_SHA256=" + SHA256, flush=True)
    return executable


def verify_result(text, rc, expected_hoot):
    expected = {
        "test_desktop_layout",
        "test_mobile_layout",
        "test_hoot_dashboard_and_existing_controls",
    }
    observed = set(re.findall(r"Starting TestKPIDashboardBrowser\.(test_\w+)", text))
    if rc or observed != expected or not re.search(r"0 failed, 0 error\(s\) of 3 tests", text):
        raise RuntimeError("HttpCase no confirmó sus tres casos de navegador")
    if re.search(
        r"(Chrome executable not found|websocket-client module is not installed|"
        r"Failed to detect chrome devtools port|skipped)",
        text,
        re.I,
    ):
        raise RuntimeError("Un navegador omitido no cuenta como prueba aprobada")
    if "[HOOT] Test suite succeeded" not in text:
        raise RuntimeError("Falta el resultado nativo de HOOT")
    if not expected_hoot or not re.search(rf"Passed {expected_hoot} tests \(", text):
        raise RuntimeError("La población ejecutada por HOOT no coincide con sus contratos")
    print(f"CI_KPI_BROWSER=PASSED CASES=3 HOOT={expected_hoot}", flush=True)


def main():
    repo = Path(sys.argv[1]).resolve()
    config, addons = sys.argv[2:4]
    temporary = Path(os.environ["RUNNER_TEMP"]).resolve()
    if repo.name != "mc_rov" or str(repo).startswith(
        ("/opt/odoo/custom-addons", "/opt/odoo/staging-addons")
    ):
        raise RuntimeError("El navegador exige un checkout aislado de CI")
    with tempfile.TemporaryDirectory(prefix="mc-rov-browser-", dir=temporary) as workspace:
        executable = prepare_browser(Path(workspace))
        environment = {**os.environ, "ODOO_BROWSER_BIN": str(executable)}
        command = [
            "odoo",
            "-d",
            "odoo_test",
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
            "^odoo_test$",
            "--log-level",
            "test",
            "--logfile",
            "",
            "--config",
            config,
            "--addons-path",
            addons,
        ]
        with tempfile.NamedTemporaryFile(
            prefix="mc-rov-tests.browser-", suffix=".log", dir=temporary, mode="w", delete=False
        ) as log:
            with subprocess.Popen(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                env=environment,
            ) as process:
                for line in process.stdout:
                    print(line, end="", flush=True)
                    log.write(line)
                rc = process.wait()
        expected_hoot = sum(
            len(re.findall(r"^\s*test\(", path.read_text(encoding="utf-8"), re.M))
            for path in (repo / "static" / "tests").glob("*.test.js")
        )
        verify_result(Path(log.name).read_text(encoding="utf-8"), rc, expected_hoot)


if __name__ == "__main__":
    main()

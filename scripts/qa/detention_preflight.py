"""Diagnóstico técnico READ ONLY, sin registros individuales ni configuración secreta."""

# Salida JSON CLI, no logging de un modelo Odoo.
# pylint: disable=unknown-option-value,print-used

import ast
import base64
import hashlib
import json
from pathlib import Path
import subprocess
import sys


def command(*arguments):
    result = subprocess.run(arguments, capture_output=True, text=True, check=False)
    return {"exit_code": result.returncode, "stdout": result.stdout.strip()}


def diagnose(baseline):
    """Solo servicios/metadatos PostgreSQL y huellas del módulo instalado."""
    addon = Path("/opt/odoo/staging-addons/mc_rov")
    report = {
        "read_only": True,
        "staging_service": command("systemctl", "is-active", "odoo-staging"),
        "staging_pid": command(
            "systemctl", "show", "odoo-staging", "--property=MainPID", "--value"
        ),
        "database_version": command(
            "sudo",
            "-u",
            "postgres",
            "psql",
            "-X",
            "-d",
            "odoo_staging",
            "-Atc",
            "SELECT latest_version FROM ir_module_module WHERE name='mc_rov'",
        ),
        "postgres_version_num": command(
            "sudo",
            "-u",
            "postgres",
            "psql",
            "-X",
            "-d",
            "odoo_staging",
            "-Atc",
            "SHOW server_version_num",
        ),
    }
    report["root_identity"] = command("id", "-u")
    version = report["postgres_version_num"]
    if version["exit_code"] == 0 and version["stdout"].isdigit():
        major = int(version["stdout"]) // 10000
        binary = Path(f"/usr/lib/postgresql/{major}/bin")
        report["postgres_tools"] = {
            name: (binary / name).is_file()
            for name in ("initdb", "pg_ctl", "psql", "pg_dump", "pg_restore", "createdb")
        }
    manifest = addon / "__manifest__.py"
    report["manifest_version"] = ast.literal_eval(manifest.read_text(encoding="utf-8"))["version"]
    mismatches = []
    for name, expected in baseline.items():
        file = addon / name
        if not file.is_file() or not file.resolve().is_relative_to(addon.resolve()):
            mismatches.append({"file": name, "status": "missing_or_external"})
            continue
        data = file.read_bytes()
        if file.suffix not in (".ttf", ".png", ".jpg", ".woff", ".woff2"):
            data = data.replace(b"\r\n", b"\n")
        if hashlib.sha256(data).hexdigest() != expected:
            mismatches.append({"file": name, "status": "different_hash"})
    report["product_files_checked"] = len(baseline)
    report["product_mismatches"] = mismatches
    print(json.dumps(report, ensure_ascii=True))


if __name__ == "__main__":
    diagnose(json.loads(base64.b64decode(sys.argv[1])))

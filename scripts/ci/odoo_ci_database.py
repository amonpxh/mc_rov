"""Crea una base vacía por ejecución y retira únicamente la que creó."""

import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import uuid


def database_name():
    """Genera un nombre ajeno a bases permanentes y copias de carreras."""
    return "mc_rov_ci_" + uuid.uuid4().hex


def validate_name(database):
    """Rechaza destinos fuera del conjunto temporal del runner."""
    if not re.fullmatch(r"mc_rov_ci_[a-f0-9]{32}", database):
        raise ValueError("Nombre de base temporal CI no permitido")


def run_isolated(database, create, execute, drop):
    """Siempre limpia tras crear con éxito, incluso si Odoo falla."""
    validate_name(database)
    create(database)
    try:
        return execute(database)
    finally:
        drop(database)


def main():
    """Ejecuta el script de pruebas con un filestore privado y sin datos previos."""
    # pylint: disable=import-outside-toplevel
    from odoo import sql_db
    from odoo.tools import SQL, config

    repo = Path(__file__).resolve().parents[2]
    workspace = Path(os.environ["GITHUB_WORKSPACE"]).resolve()
    if repo != workspace / "ci-addons" / "mc_rov" or os.environ.get("GITHUB_ACTIONS") != "true":
        raise RuntimeError("La base temporal exige el checkout del runner GitHub")
    conf = "/etc/odoo/odoo.conf"
    config.parse_config(["-c", conf, "--no-http", "--max-cron-threads", "0"])

    def admin(database, statement):
        validate_name(database)
        with sql_db.db_connect("postgres").cursor() as cursor:
            cursor._cnx.autocommit = True  # pylint: disable=protected-access
            cursor.execute(SQL(statement, SQL.identifier(database)))

    lifecycle = Path(os.environ["RUNNER_TEMP"]) / "mc-rov-tests.database.lifecycle.log"

    def record(marker):
        print(marker, flush=True)
        with lifecycle.open("a", encoding="utf-8") as log:
            log.write(marker + "\n")

    with tempfile.TemporaryDirectory(prefix="mc-rov-ci-", dir=os.environ["RUNNER_TEMP"]) as data:

        def create(database):
            admin(database, "CREATE DATABASE %s TEMPLATE template0")
            record(f"CI_ODOO_DATABASE=CREATED NAME={database} TEMPLATE=template0")

        def drop(database):
            admin(database, "DROP DATABASE %s WITH (FORCE)")
            record(f"CI_ODOO_DATABASE=DROPPED NAME={database}")

        def execute(database):
            subprocess.run(
                ["bash", str(repo / "scripts/ci/run_odoo_tests.sh"), sys.argv[1]],
                env={**os.environ, "MC_ROV_CI_DATABASE": database, "MC_ROV_CI_DATA_DIR": data},
                check=True,
            )

        run_isolated(database_name(), create, execute, drop)


if __name__ == "__main__":
    main()

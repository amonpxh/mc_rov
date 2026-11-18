#!/usr/bin/env bash
# Pruebas propias en copia nueva; jamás instala ni reinicia un servicio operativo.
set -euo pipefail
umask 077
PAYLOAD=${1:?directorio de paquete requerido}
[[ "$PAYLOAD" =~ ^/var/tmp/mc-rov-detention-red-[a-f0-9]{32}$ ]]
test "$(id -u)" = 0
CONF=/etc/odoo/odoo-staging.conf
ADDON=/opt/odoo/staging-addons/mc_rov
SOURCE=odoo_staging
echo DETENTION_RED_PHASE=source-preflight
systemctl is-active --quiet odoo-staging
PID=$(systemctl show odoo-staging --property=MainPID --value)
command -v unshare > /dev/null
unshare --net -- true
test "$(sudo -u postgres psql -X -d "$SOURCE" -Atc "SELECT latest_version FROM ir_module_module WHERE name='mc_rov'")" = 19.0.25.2.0
PG_MAJOR=$(sudo -u postgres psql -X -d "$SOURCE" -Atc "SELECT current_setting('server_version_num')::int/10000")
[[ "$PG_MAJOR" =~ ^[1-9][0-9]$ ]]
PG_BIN=/usr/lib/postgresql/$PG_MAJOR/bin
test -x "$PG_BIN/initdb"
test -x "$PG_BIN/pg_ctl"
WORK=$(mktemp -d /var/tmp/mc-rov-detention-red-XXXXXX)
DB=mc_rov_detention_red_$(basename "$WORK" | awk -F- '{print $NF}')
[[ "$DB" =~ ^mc_rov_detention_red_[a-zA-Z0-9]{6}$ ]]
SOCKET=$WORK/socket
CREATED=0
CLUSTER_STARTED=0
finish() {
    rc=$?
    trap - EXIT
    set +e
    if test "$CREATED" = 1; then
        sudo -u postgres "$PG_BIN/psql" -h "$SOCKET" -p 55432 -X -d postgres -v ON_ERROR_STOP=1 -c "ALTER DATABASE \"$DB\" WITH ALLOW_CONNECTIONS false" > "$WORK/block.log" 2>&1
        blocked=$?
        sudo -u postgres "$PG_BIN/psql" -h "$SOCKET" -p 55432 -X -d postgres -v ON_ERROR_STOP=1 -c "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname='$DB' AND pid<>pg_backend_pid()" >> "$WORK/block.log" 2>&1
        terminated=$?
        if test "$blocked" != 0 || test "$terminated" != 0; then rc=1; else echo DETENTION_RED_COPY_CONNECTIONS_BLOCKED=True; fi
    fi
    if test "$CLUSTER_STARTED" = 1; then
        sudo -u postgres "$PG_BIN/pg_ctl" -D "$WORK/postgres" -m fast -w stop >> "$WORK/block.log" 2>&1
        if test "$?" != 0; then rc=1; else echo DETENTION_RED_PRIVATE_POSTGRES_STOPPED=True; fi
    fi
    systemctl is-active --quiet odoo-staging || rc=1
    test "$(systemctl show odoo-staging --property=MainPID --value)" = "$PID" || rc=1
    echo "DETENTION_RED_WORK=$WORK"
    echo "DETENTION_RED_DATABASE=$DB"
    if test -f "$WORK/tests.log"; then
        echo DETENTION_RED_LOG_BEGIN
        base64 -w0 "$WORK/tests.log"
        echo
        echo DETENTION_RED_LOG_END
    fi
    if test "$rc" = 0; then
        echo DETENTION_RED_STAGING_PID_UNCHANGED=True
        echo DETENTION_RED=PASSED
    fi
    exit "$rc"
}
trap finish EXIT
trap 'exit 130' INT
trap 'exit 143' TERM HUP
chmod 755 "$WORK"
mkdir -m 700 "$WORK/backup"
python3 "$PAYLOAD/check_baseline.py" "$ADDON" "$PAYLOAD/baseline.json" "$PAYLOAD/observed-source.json" "$WORK/source-before.json" before
echo DETENTION_RED_BASELINE=PASSED
SOURCE_DATA=$(sudo -H -u odoo python3 - "$CONF" <<'PY'
import sys
from odoo.tools import config
config.parse_config(['-c', sys.argv[1]])
assert config['db_user'] == 'odoo'
assert config['db_host'] in (False, None, '', 'localhost', '/var/run/postgresql')
print(config['data_dir'])
PY
)
test -d "$SOURCE_DATA/filestore/$SOURCE"
test -z "$(find "$SOURCE_DATA/filestore/$SOURCE" -type l -print -quit)"
DB_BYTES=$(sudo -u postgres psql -X -d "$SOURCE" -Atc "SELECT pg_database_size(current_database())")
FILE_BYTES=$(du -sb "$SOURCE_DATA/filestore/$SOURCE" | cut -f1)
REQUIRED=$((4*DB_BYTES + 2*FILE_BYTES + 536870912))
test "$(df -PB1 "$WORK" | awk 'NR==2 {print $4}')" -gt "$REQUIRED"
sudo -u postgres "$PG_BIN/pg_dump" -Fc "$SOURCE" > "$WORK/backup/staging.dump"
test -s "$WORK/backup/staging.dump"
sudo -u postgres "$PG_BIN/pg_restore" --list < "$WORK/backup/staging.dump" > "$WORK/backup/staging.contents"
# PostgreSQL propio: la copia nunca aparece en el clúster que descubren los Odoo
# operativos. Red aislada, sin TCP; solamente socket privado y autenticación peer.
echo DETENTION_RED_PHASE=create-private-postgres
install -d -m 700 -o postgres -g postgres "$WORK/postgres"
install -d -m 755 -o postgres -g postgres "$SOCKET"
unshare --net -- runuser -u postgres -- "$PG_BIN/initdb" -D "$WORK/postgres" --auth-local=peer --auth-host=reject --encoding=UTF8 --locale=C.UTF-8 > "$WORK/initdb.log" 2>&1
CLUSTER_STARTED=1
unshare --net -- runuser -u postgres -- "$PG_BIN/pg_ctl" -D "$WORK/postgres" -l "$WORK/postgres/server.log" -o "-h '' -k '$SOCKET' -p 55432" -w start > "$WORK/pg-start.log" 2>&1
sudo -u postgres "$PG_BIN/psql" -h "$SOCKET" -p 55432 -X -d postgres -v ON_ERROR_STOP=1 -c 'CREATE ROLE odoo LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION' > /dev/null
sudo -u postgres "$PG_BIN/createdb" -h "$SOCKET" -p 55432 -T template0 -O odoo "$DB"
CREATED=1
echo DETENTION_RED_PHASE=restore-private-copy
sudo -u postgres "$PG_BIN/pg_restore" -h "$SOCKET" -p 55432 --exit-on-error --no-owner --role=odoo -d "$DB" < "$WORK/backup/staging.dump" > "$WORK/restore.log" 2>&1
mkdir -p "$WORK/addons/mc_rov" "$WORK/data/filestore/$DB"
python3 - "$PAYLOAD" "$WORK" <<'PY'
import pathlib, sys, tarfile
payload, work = map(pathlib.Path, sys.argv[1:])
with tarfile.open(payload / 'source.tar') as archive:
    for member in archive.getmembers():
        path = pathlib.PurePosixPath(member.name)
        assert not path.is_absolute() and '..' not in path.parts
        assert member.isdir() or member.isfile(), 'No se aceptan enlaces ni dispositivos'
    archive.extractall(work / 'addons/mc_rov', filter='data')
root = work / 'addons/mc_rov/tests'
(root / 'test_detention_capture.py').write_bytes((payload / 'test_detention_capture.py').read_bytes())
with (root / '__init__.py').open('a') as output:
    output.write('\nfrom . import test_detention_capture\n')
PY
cp -a "$SOURCE_DATA/filestore/$SOURCE/." "$WORK/data/filestore/$DB/"
python3 - "$CONF" "$WORK" <<'PY'
import configparser, pathlib, sys
original, work = sys.argv[1], pathlib.Path(sys.argv[2])
config = configparser.ConfigParser(interpolation=None)
assert config.read(original)
options = config['options']
options['addons_path'] = str(work / 'addons') + ',' + options['addons_path']
options['data_dir'] = str(work / 'data')
options['db_host'] = str(work / 'socket')
options['db_port'] = '55432'
options['workers'] = '0'
options['max_cron_threads'] = '0'
with (work / 'isolated.conf').open('w') as output:
    config.write(output)
PY
chown root:odoo "$WORK/isolated.conf"
chmod 640 "$WORK/isolated.conf"
chown -R odoo:odoo "$WORK/addons" "$WORK/data"
install -d -m 700 -o odoo -g odoo "$WORK/evidence"
sudo -u postgres "$PG_BIN/psql" -h "$SOCKET" -p 55432 -X -d "$DB" -v ON_ERROR_STOP=1 -c 'UPDATE ir_cron SET active=false' > /dev/null
# Confirmar resolución de módulo y filestore antes de ejecutar una sola prueba.
sudo -H -u odoo python3 - "$WORK/isolated.conf" "$WORK" <<'PY'
import pathlib, sys
from odoo.tools import config
from odoo.modules.module import get_module_path, initialize_sys_path
work = pathlib.Path(sys.argv[2])
config.parse_config(['-c', sys.argv[1]])
initialize_sys_path()
assert pathlib.Path(get_module_path('mc_rov')).resolve() == (work / 'addons/mc_rov').resolve()
assert pathlib.Path(config['data_dir']).resolve() == (work / 'data').resolve()
assert pathlib.Path(config['db_host']).resolve() == (work / 'socket').resolve()
assert config['db_port'] == 55432
PY
echo DETENTION_RED_PHASE=upgrade-isolated-copy-and-native-contracts
# Solo la copia pasa de la versión de datos observada a la base de código probada.
# La red se aísla antes de cargar Odoo; solo PostgreSQL local por socket Unix.
set +e
unshare --net -- runuser -u odoo -- timeout --signal=TERM --kill-after=20s 600s \
    odoo -c "$WORK/isolated.conf" -d "$DB" -u mc_rov --test-tags detention_capture \
    --db-filter "^$DB$" --stop-after-init --no-http --workers 0 --max-cron-threads 0 \
    --log-level test --logfile "$WORK/evidence/tests.log" > "$WORK/console.log" 2>&1
TEST_RC=$?
set -e
sudo -H -u odoo cat "$WORK/evidence/tests.log" > "$WORK/tests.log"
echo "DETENTION_RED_TEST_RC=$TEST_RC"
python3 "$PAYLOAD/verify_detention_red.py" "$PAYLOAD/expected.json" "$WORK/tests.log" "$TEST_RC"
python3 "$PAYLOAD/check_baseline.py" "$ADDON" "$PAYLOAD/baseline.json" "$PAYLOAD/observed-source.json" "$WORK/source-before.json" after
echo DETENTION_RED_SOURCE_FILES_UNCHANGED=True

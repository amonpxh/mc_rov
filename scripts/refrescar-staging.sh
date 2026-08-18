#!/usr/bin/env bash
#
# Rehace odoo_staging a partir de odoo_prod: base, filestore y neutralización.
#
# BORRA la base destino. Eso es a propósito — staging es desechable y producción no— pero
# significa que un nombre mal escrito sería catastrófico, así que hay dos guardarraíles que
# no se deben quitar: el destino tiene que llamarse *staging*, y no puede ser el origen.
#
# Uso:  sudo -u odoo bash scripts/refrescar-staging.sh
#
# Documentación: docs/runbooks/staging.md

set -euo pipefail

PROD_DB="${PROD_DB:-odoo_prod}"
STAGING_DB="${STAGING_DB:-odoo_staging}"
FILESTORE_ROOT="${FILESTORE_ROOT:-/var/lib/odoo/.local/share/Odoo/filestore}"
STAGING_CONF="${STAGING_CONF:-/etc/odoo/odoo-staging.conf}"

# Contraseña de los usuarios internos en staging. Se separa de la de producción a propósito:
# evita confundir las dos pestañas por memoria muscular, y una credencial de staging filtrada
# deja de ser una credencial de producción.
#
# El valor por defecto es débil y visible, y eso es una decisión, no un descuido: **el control
# de acceso real es el túnel SSH**. Odoo escucha en 127.0.0.1 y staging no está publicado en el
# firewall, así que para llegar al formulario de login ya hay que tener acceso al servidor.
#
# **Si alguien alguna vez expone staging más allá del túnel, esta contraseña pasa a ser lo único
# que protege una copia completa de los datos de producción.** Ese día hay que exportar
# STAGING_PASSWORD con algo serio — no escribirla acá, que este archivo está versionado.
STAGING_PASSWORD="${STAGING_PASSWORD:-staging}"

# --- Guardarraíles -------------------------------------------------------------------------

case "$STAGING_DB" in
    *staging*) ;;
    *)
        echo "RECHAZADO: «$STAGING_DB» no parece una base de staging." >&2
        echo "Este script borra la base destino. Solo acepta nombres que contengan 'staging'." >&2
        exit 1
        ;;
esac

if [ "$STAGING_DB" = "$PROD_DB" ]; then
    echo "RECHAZADO: origen y destino son la misma base ($PROD_DB)." >&2
    exit 1
fi

if ! psql -lqt | cut -d '|' -f 1 | grep -qw "$PROD_DB"; then
    echo "RECHAZADO: no existe la base de origen «$PROD_DB»." >&2
    exit 1
fi

echo "==> Origen: $PROD_DB   Destino: $STAGING_DB"

# --- 1. Cerrar conexiones abiertas ----------------------------------------------------------
# Postgres no borra una base en uso, y staging casi siempre tiene una instancia levantada.

echo "==> Cerrando conexiones a $STAGING_DB"
psql -d postgres -q -c "
    SELECT pg_terminate_backend(pid)
      FROM pg_stat_activity
     WHERE datname = '$STAGING_DB' AND pid <> pg_backend_pid();" >/dev/null

# --- 2. Copiar la base ----------------------------------------------------------------------
# pg_dump no toma bloqueos que molesten a la instancia de producción: se puede correr en
# caliente, sin ventana de mantención.

echo "==> Recreando $STAGING_DB desde $PROD_DB"
dropdb --if-exists "$STAGING_DB"
createdb "$STAGING_DB"
pg_dump "$PROD_DB" | psql -q -d "$STAGING_DB" >/dev/null

# --- 3. Copiar el filestore -----------------------------------------------------------------
# Los adjuntos no viven en la base. Sin esto, cada archivo de staging da 404 y alguien va a
# reportarlo como un bug del módulo.

if [ -d "$FILESTORE_ROOT/$PROD_DB" ]; then
    echo "==> Copiando filestore"
    rm -rf "${FILESTORE_ROOT:?}/${STAGING_DB:?}"
    cp -a "$FILESTORE_ROOT/$PROD_DB" "$FILESTORE_ROOT/$STAGING_DB"
else
    echo "==> Sin filestore en $FILESTORE_ROOT/$PROD_DB — se omite"
fi

# --- 4. Neutralizar -------------------------------------------------------------------------
# NO ES OPCIONAL. Una copia de producción trae los correos reales de los clientes y las
# acciones planificadas activas. Se rehace en cada refresco porque cada refresco vuelve a
# traer la configuración viva de producción.

echo "==> Neutralizando"
psql -q -d "$STAGING_DB" >/dev/null <<'SQL'
UPDATE ir_cron SET active = false;
UPDATE ir_mail_server SET active = false;

DO $$
BEGIN
    IF to_regclass('public.fetchmail_server') IS NOT NULL THEN
        EXECUTE 'UPDATE fetchmail_server SET active = false';
    END IF;
END
$$;

-- Dos bases no pueden reclamar la misma suscripción Enterprise.
UPDATE ir_config_parameter
   SET value = gen_random_uuid()::text
 WHERE key = 'database.uuid';

-- Para saber desde adentro en qué base se está mirando.
INSERT INTO ir_config_parameter (key, value)
     VALUES ('mc_rov.entorno', 'STAGING')
ON CONFLICT (key) DO UPDATE SET value = 'STAGING';
SQL

CRONS=$(psql -tAq -d "$STAGING_DB" -c "SELECT count(*) FROM ir_cron WHERE active;")
CORREOS=$(psql -tAq -d "$STAGING_DB" -c "SELECT count(*) FROM ir_mail_server WHERE active;")

echo "==> Verificación: $CRONS cron(es) activos, $CORREOS servidor(es) de correo activos"

if [ "$CRONS" != "0" ] || [ "$CORREOS" != "0" ]; then
    echo "AVISO: la neutralización no dejó todo en cero. Revisar antes de levantar staging." >&2
    exit 1
fi

# --- 5. Contraseña propia de staging ---------------------------------------------------------
# Va por `odoo shell` y no por SQL: la contraseña tiene que pasar por el hasheo de Odoo, y un
# UPDATE con texto plano deja al usuario sin poder entrar a ninguna parte.
#
# Se aplica a los usuarios internos activos (`share = False`), que son los que tienen login de
# backend. Los técnicos, el público y las plantillas de portal quedan fuera.
#
# Hay que rehacerlo en cada refresco, porque el dump vuelve a traer los hashes de producción.

if [ -f "$STAGING_CONF" ]; then
    echo "==> Aplicando contraseña de staging"
    STAGING_PASSWORD="$STAGING_PASSWORD" odoo shell -d "$STAGING_DB" -c "$STAGING_CONF" \
        --no-http --log-level=warn <<'PY'
import os

usuarios = env["res.users"].search([("share", "=", False), ("active", "=", True)])
usuarios.write({"password": os.environ["STAGING_PASSWORD"]})
env.cr.commit()
print("    %s usuario(s) interno(s) actualizados" % len(usuarios))
PY
else
    echo "==> Sin $STAGING_CONF — se omite la contraseña de staging"
    echo "    (normal en el primer llenado, si la configuración todavía no existe)"
fi

echo "==> Listo. Levantar con: odoo -c $STAGING_CONF"

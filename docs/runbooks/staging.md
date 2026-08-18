# Runbook: staging

**Audience:** anyone who is about to change `odoo_prod` and would rather rehearse it first.

**Time:** ~30 minutes one-time setup, ~2 minutes per refresh.

---

## Why this exists

Every change to this module has been deployed straight to production, migrations included.
That worked because production is nearly empty — 4 serials and 2 work lines — so a migration
that damaged data would have damaged almost nothing.

**That stops being true very soon**, and three things arrive together: the real ROV product
load, the `X` bump that drops the fabrication columns, and MRP + Quality, which touch inventory
for real. Rehearsing a migration for the first time *after* the data is loaded is rehearsing it
when it can no longer go wrong safely.

## The condition that makes staging worth anything

**Staging must run its own checkout of the code.**

Production serves `/opt/odoo/custom-addons/mc_rov`. A second database pointed at *that same
directory* runs the code that is already in production, so it rehearses nothing — it only proves
that today's code still works on a copy of today's data.

Staging gets `/opt/odoo/staging-addons/mc_rov`, where you check out the PR branch **before** it
is merged.

This also removes half of a known problem: the CI runner's workspace currently lives inside the
production addons directory, so a CI job can change what Odoo is serving. Three separate
checkouts — production, staging, CI — is the shape that ends it.

## Staging environment

| Resource | Value |
|---|---|
| Module path | `/opt/odoo/staging-addons/mc_rov` |
| Database | `odoo_staging` |
| Config | `/etc/odoo/odoo-staging.conf` |
| HTTP port | `8070` (production keeps `8069`) |
| Log file | `/var/log/odoo/odoo-staging.log` |

**`odoo_staging` is not `odoo_lab`.** Staging is a refreshable copy of production, for
rehearsing deploys and migrations against real data. `odoo_lab` is a throwaway database with
demo data, for evaluating whether a module does what we think it does. Different jobs, both
useful.

---

## One-time setup

### 1. Read the production config

You need its `addons_path` verbatim — the staging config is the same file with seven changes,
and guessing the Odoo and Enterprise addons directories is how you get a server that starts and
is missing half its apps.

```bash
sudo cat /etc/odoo/odoo.conf
```

### 2. Create the staging checkout

```bash
sudo -H -u odoo mkdir -p /opt/odoo/staging-addons && \
sudo -H -u odoo git clone /opt/odoo/custom-addons/mc_rov /opt/odoo/staging-addons/mc_rov && \
sudo -H -u odoo git -C /opt/odoo/staging-addons/mc_rov remote set-url origin git@github.com:amonpxh/mc_rov.git && \
sudo -H -u odoo git -C /opt/odoo/staging-addons/mc_rov fetch origin
```

Cloning from the local production checkout instead of GitHub is deliberate: it is faster and it
works even if the deploy key only allows one origin. The remote is repointed straight after, so
`fetch` brings branches from GitHub and not from production.

### 3. Write the staging config

`odoo.conf` needs **seven** changes. Since you are root, build it with `sed` rather than by
hand — the `diff` at the end is the check:

```bash
sed -e 's/^db_name = odoo_prod$/db_name = odoo_staging/'     -e 's/^dbfilter = \^odoo_prod\$$/dbfilter = ^odoo_staging$/'     -e 's#odoo-server\.log#odoo-staging.log#'     -e 's#/opt/odoo/custom-addons#/opt/odoo/staging-addons#'     -e 's/^workers = 3$/workers = 0/'     -e 's/^max_cron_threads = 1$/max_cron_threads = 0/'     /etc/odoo/odoo.conf > /etc/odoo/odoo-staging.conf && echo "http_port = 8070" >> /etc/odoo/odoo-staging.conf && chown odoo:odoo /etc/odoo/odoo-staging.conf && chmod 640 /etc/odoo/odoo-staging.conf && diff /etc/odoo/odoo.conf /etc/odoo/odoo-staging.conf
```

| Key | Value | Why |
|---|---|---|
| `db_name` | `odoo_staging` | |
| `dbfilter` | `^odoo_staging$` | **Miss this one and staging says «database not found» with no hint why.** Production filters to `^odoo_prod$`, so a copied config refuses to serve the staging database at all |
| `logfile` | `/var/log/odoo/odoo-staging.log` | Sharing production's log makes both unreadable |
| `addons_path` | `/opt/odoo/custom-addons` → `/opt/odoo/staging-addons` | **The one that ruins the day** — see below |
| `http_port` | `8070` | Not present in production's config, so it must be added; the default is 8069 |
| `workers` | `0` | One process for one person. Production runs three on this same machine |
| `max_cron_threads` | `0` | Belt and braces: the refresh script deactivates every cron, this stops the runner too |

**Leave `data_dir` alone** — it is unset, so it defaults to `/var/lib/odoo/.local/share/Odoo`,
the filestore lives per database underneath it, and the refresh script relies on that layout.

**Leave `http_interface = 127.0.0.1` alone.** Odoo listens on localhost behind the reverse
proxy, so staging is not reachable from outside and the SSH tunnel below is not a fallback — it
is the only way in. That is the safer arrangement anyway.

> **The one that ruins the day:** if `addons_path` still points at `/opt/odoo/custom-addons`,
> staging serves production's code and every rehearsal is a false pass. If that line does not
> show up in the `diff`, stop and fix it before going on.

### 4. First fill

```bash
sudo -u odoo bash /opt/odoo/staging-addons/mc_rov/scripts/refrescar-staging.sh
```

### 5. Start it

```bash
sudo -u odoo odoo -c /etc/odoo/odoo-staging.conf
```

It holds the terminal on purpose — `Ctrl+C` closes it. Production keeps running on 8069 without
noticing.

**Reaching it needs an SSH tunnel**, because `http_interface = 127.0.0.1`: Odoo listens only on
localhost, behind the reverse proxy. From your own machine:

```bash
ssh -L 8070:localhost:8070 root@<server-ip>
```

then open `http://localhost:8070`. Nothing has to be opened on the firewall, which is the safer
arrangement — staging holds a copy of production's data and has no business being reachable from
the internet.

---

## Using it, per pull request

```bash
# 1. Put staging on the branch you want to rehearse. NOT main.
sudo -H -u odoo git -C /opt/odoo/staging-addons/mc_rov fetch origin && \
sudo -H -u odoo git -C /opt/odoo/staging-addons/mc_rov checkout -B rehearsal origin/<branch>

# 2. Refresh the data, so the migration runs against what production actually holds
sudo -u odoo bash /opt/odoo/staging-addons/mc_rov/scripts/refrescar-staging.sh

# 3. Run the upgrade — this is the rehearsal
sudo -u odoo odoo -c /etc/odoo/odoo-staging.conf -u mc_rov --stop-after-init --no-http

# 4. Read what the migration said about real data
sudo grep -i "mc_rov 19" /var/log/odoo/odoo-staging.log | tail -30

# 5. Look at it
sudo -u odoo odoo -c /etc/odoo/odoo-staging.conf
```

Only after that: merge, and deploy to production with
[`deploy.md`](deploy.md).

**Step 4 is the point of the whole exercise.** Migration scripts in this module log how many
rows they touched, and several of them log what they discarded. `19.0.15.0.0` would have dumped
every extra run it dropped — on production that log line arrived *after* the rows were gone.

---

## Refreshing

`scripts/refrescar-staging.sh` **drops `odoo_staging` and rebuilds it from production.**
Anything typed into staging is gone. That is the intent: staging is disposable, production is
not.

It refuses to run if the target database name does not contain `staging`, and if source and
target are the same. Those two guards are the only thing between a typo and a dropped
production database, so do not remove them.

What it does, in order:

1. Kills open connections to `odoo_staging` — Postgres will not drop a database in use.
2. Drops and recreates it, then pipes `pg_dump odoo_prod` into it. **No downtime on
   production**: `pg_dump` does not lock anything a running Odoo needs.
3. Copies the filestore. Attachments do not live in the database, so without this every file in
   staging is a 404.
4. **Neutralises it.** Not optional — see below.

## Neutralising, and why it is not optional

A copy of production contains **your customers' real email addresses** and their scheduled
actions, active.

The script deactivates every `ir.cron`, every outgoing mail server, and any incoming ones, and
it regenerates `database.uuid` so two databases do not claim the same Enterprise subscription.
It also writes a system parameter `mc_rov.entorno = STAGING`, which is how you tell from inside
which database you are looking at.

**Every refresh re-neutralises**, because every refresh brings production's live settings back.

> If someone ever restores this dump anywhere else by hand, neutralise it by hand too. The
> failure mode is not a broken server — it is a real email to a real customer from a database
> that was supposed to be a rehearsal.

## What staging does not cover

- **Load.** One person clicking is not the concurrency of a working day.
- **Anything scheduled**, since the crons are off by design. A change to a scheduled action has
  to be tested by triggering it by hand.
- **Server-level state** — Postgres version, disk, the systemd unit. Staging shares the machine
  with production, so it proves nothing about the machine.

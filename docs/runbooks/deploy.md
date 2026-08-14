# Runbook: Deploy mc_rov to production

**Audience:** anyone deploying a change to the production Odoo instance.

**Time to deploy:** ~3 minutes assuming no errors.

**Escalate to:** tech lead if Odoo doesn't restart cleanly or errors appear in the log.

---

## Production environment

| Resource | Value |
|---|---|
| Module path | `/opt/odoo/custom-addons/mc_rov` |
| Database | `odoo_prod` |
| Log file | `/var/log/odoo/odoo-server.log` |
| Config | `/etc/odoo/odoo.conf` |
| Odoo service | `odoo` (systemd) |

## Pre-deploy checklist

- [ ] PR is merged into `main`
- [ ] CI is green (lint + tests passed on the merge commit)
- [ ] You have SSH access to the production VPS via a deploy key (not personal key)
- [ ] If the change includes a migration: the migration script is in `migrations/<version>/post-migrate.py` and has been reviewed
- [ ] **If the change alters how a stored computed field is calculated:** the ORM does not recompute a field whose column already exists with data. Either the change only needs to apply going forward, or it needs a `post-migrate` — and by the versioning table in `CLAUDE.md`, needing one makes it an `X` bump.

## Deploy procedure

> **Run every git command as `odoo`, never as root.** Root has no deploy key and never
> had one; a plain `git pull` fails with `Permission denied (publickey)`. See "Why not
> root" below.

```bash
# 1. SSH to production VPS

# 2. Bring the working tree to main.
#    As odoo: it owns the repo and holds the deploy key. As root, the fetch fails, and
#    any git command that does succeed leaves root-owned objects in .git that break the
#    CI runner's next checkout.
#    --ff-only refuses rather than inventing a merge if the tree has diverged.
sudo -H -u odoo git -C /opt/odoo/custom-addons/mc_rov fetch origin
sudo -H -u odoo git -C /opt/odoo/custom-addons/mc_rov merge --ff-only origin/main

#    Confirm you are on the commit you think you are, BEFORE touching the database.
#    Deploying the wrong migration onto odoo_prod is not undone by a git checkout.
git -C /opt/odoo/custom-addons/mc_rov log --oneline -1
grep version /opt/odoo/custom-addons/mc_rov/__manifest__.py

# 3. Update the module (re-applies new migrations if any)
sudo -u odoo odoo \
  -u mc_rov \
  --stop-after-init \
  --no-http \
  --config /etc/odoo/odoo.conf

# 4. Restart the service. NOT OPTIONAL — see below.
sudo systemctl restart odoo

# 5. Prove the restart happened.
systemctl status odoo --no-pager | head -4
```

### Step 3 prints nothing. That is normal.

`odoo.conf` sets `logfile`, so everything — migration output and any traceback alike —
goes to `/var/log/odoo/odoo-server.log`. All you see on screen is a few docutils warnings
about the README, which are harmless. It looks like the command did nothing. To read what
actually happened:

```bash
sudo grep "mc_rov:" /var/log/odoo/odoo-server.log | tail -20
```

### Step 4 is the one people skip, and it fails in a confusing way

Step 3 runs a **separate** Odoo process that updates the database and exits. The live
workers keep the Python registry they loaded at boot. Skip the restart and the database
now holds views referring to fields the running process has never heard of. The symptom is
an Owl error in the browser:

```
"stock.lot"."mc_propietario_id" field is undefined.
```

which reads like a broken deploy rather than a missing restart. It happened on 2026-08-07
and went unnoticed for four days.

**In step 5, read the `Active: ... since` line.** It must show the current time. If it
shows a time before step 3, the restart did not happen and the form is still broken.

## Why not root

The remote is SSH (`git@github.com:amonpxh/mc_rov.git`). The deploy key belongs to the
`odoo` user, which also owns `/opt/odoo/custom-addons/mc_rov`. Root has no key — the first
attempt on 2026-08-07 was also the first time root had ever connected to GitHub, and it
stopped to ask about the host fingerprint. `sudo -H -u odoo` is the whole fix: `-H` sets
`HOME` so `ssh` finds the key.

## Known issue: the runner shares this directory

`/opt/odoo/custom-addons/mc_rov` is both the production addons path **and** the CI runner's
workspace. The deploy above does not depend on that — it fetches on its own — but the
sharing has its own consequence: **a CI run can change what production is serving**, since
the checkout lands in the live addons path. Deploying is not the only thing that moves this
code.

Separating the two is tracked in [`docs/pendientes.md`](../pendientes.md).

> An earlier version of this runbook claimed the deploy *depended* on CI having fetched,
> and presented `merge --ff-only` as a workaround. That was wrong: the `odoo` user fetches
> perfectly well on its own. Corrected 2026-08-11.

## Verification

After deploying:

```bash
# 1. Check the log for errors during module update
tail -20 /var/log/odoo/odoo-server.log
```

**Expected:** no lines starting with `ERROR`. Look for healthy startup messages like `Registry loaded`.

Then:

2. Open Odoo in a browser.
3. Navigate to the affected feature (the one your change touched).
4. Confirm visually that it works as expected.

## Rollback

If the deploy breaks production:

```bash
# 1. Revert the merge commit on main (on your dev machine)
git checkout main
git pull
git revert <bad-commit-sha>
git push origin main

# 2. Re-deploy the reverted state (on the VPS).
#    Same rule as the deploy: git as odoo, never as root. This block used to say
#    `cd … && git pull`, which fails with Permission denied (publickey) — the one
#    failure you least want to discover during a rollback.
sudo -H -u odoo git -C /opt/odoo/custom-addons/mc_rov fetch origin
sudo -H -u odoo git -C /opt/odoo/custom-addons/mc_rov merge --ff-only origin/main
sudo -u odoo odoo -u mc_rov --stop-after-init --no-http --config /etc/odoo/odoo.conf
sudo systemctl restart odoo
```

**If a migration was applied** and rolling forward is risky: restore from the most recent Odoo database backup. **Coordinate with tech lead before doing this** — DB restore is destructive of any changes between the snapshot and now.

## Incident log

*(append postmortems here as they occur)*

Format:

```
## YYYY-MM-DD
- Symptom:
- Root cause:
- Fix applied:
- Prevention added:
```

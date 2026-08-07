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

## Deploy procedure

> **`git pull` does not work here.** See "How the code actually arrives" below before
> deploying for the first time. The step below is the procedure that works today, not the
> one you would expect.

```bash
# 1. SSH to production VPS

# 2. Fast-forward the working tree to main.
#    Local operation, no network: origin/main is already fetched (see below).
#    Runs as odoo so the CI runner's checkout does not end up with root-owned git objects.
#    --ff-only refuses rather than inventing a merge if the tree has diverged.
sudo -H -u odoo git -C /opt/odoo/custom-addons/mc_rov merge --ff-only origin/main

#    Confirm you are on the commit you think you are, before touching the database:
git -C /opt/odoo/custom-addons/mc_rov log --oneline -1
grep version /opt/odoo/custom-addons/mc_rov/__manifest__.py

# 3. Update the module (re-applies new migrations if any)
sudo -u odoo odoo \
  -u mc_rov \
  --stop-after-init \
  --no-http \
  --config /etc/odoo/odoo.conf

# 4. Restart the Odoo service to reload Python in long-running workers
sudo systemctl restart odoo
```

**Step 3 prints nothing to the console.** `odoo.conf` sets `logfile`, so everything —
including migration output and any traceback — goes to `/var/log/odoo/odoo-server.log`.
The only thing you will see on screen is a handful of docutils warnings about the README,
which are harmless. To read what actually happened:

```bash
sudo grep "mc_rov:" /var/log/odoo/odoo-server.log | tail -20
```

## How the code actually arrives

`git pull` as `root` fails with `Permission denied (publickey)`: the remote is SSH
(`git@github.com:amonpxh/mc_rov.git`) and root has no deploy key. It never had one — the
first attempt, on 2026-08-07, was also the first time root had ever connected to GitHub.

What keeps `origin/main` current is the **CI runner**, which checks out into this very
directory (`/opt/odoo/custom-addons/mc_rov` is both the runner workspace and the production
addons path). Its fetches update the remote refs, which is why `merge --ff-only origin/main`
works offline.

Two consequences worth understanding before you rely on this:

1. **Production only sees a commit after CI has fetched it.** If the refs are stale,
   `merge --ff-only` will report "Already up to date" while main has moved on. Check
   `git -C /opt/odoo/custom-addons/mc_rov status --short --branch` — it should say `behind N`
   before you merge, and nothing after.
2. **A CI run can change what production is serving**, because the checkout lands in the
   live addons path. Deploying is not the only thing that moves this code.

Separating the runner workspace from the production addons path, and giving the deploy its
own working credential, is tracked in [`docs/pendientes.md`](../pendientes.md). Until that is
done, treat the procedure above as a workaround rather than a design.

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

# 2. Re-deploy the reverted state (on the VPS)
cd /opt/odoo/custom-addons/mc_rov
git pull origin main
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

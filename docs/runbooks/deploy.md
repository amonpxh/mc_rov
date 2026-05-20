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

```bash
# 1. SSH to production VPS

# 2. Pull the latest code from main
cd /opt/odoo/custom-addons/mc_rov
git pull origin main

# 3. Update the module (re-applies new migrations if any)
sudo -u odoo odoo \
  -u mc_rov \
  --stop-after-init \
  --no-http \
  --config /etc/odoo/odoo.conf

# 4. Restart the Odoo service to reload Python in long-running workers
sudo systemctl restart odoo
```

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

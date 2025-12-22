# 📋 Production Deployment Checklist

**Last Updated**: December 22, 2025  
**Version**: 1.0  
**For**: Grocery Store Flask + Razorpay  
**Status**: Production Ready  

---

## 🎯 Overview

This checklist ensures safe deployment of code and database changes to production without data loss or downtime.

**Time Estimate**: 20-30 minutes per deployment  
**Risk Level**: Low (with this checklist)  
**Required Tools**: bash, Python 3.7+, backup_database.py, verify_migration.py

---

## 📅 Pre-Deployment Phase (24 Hours Before)

### Day Before Checks

- [ ] **Review Changes** - What code/database changes are being deployed?
  - List files changed: _____________________________________
  - Database schema changes: ________________________________
  - Configuration changes: __________________________________

- [ ] **Notify Team** - Alert stakeholders about upcoming deployment
  - Development team: [ ] Notified
  - DevOps/Infrastructure: [ ] Notified
  - Business stakeholders: [ ] Notified
  - Deployment window: ______________ to ______________

- [ ] **Schedule Window** - Choose low-traffic time
  - Preferred time: _________________ (HH:MM UTC/IST)
  - Backup time slot: _________________ (in case issues)

- [ ] **Test on Staging** - Run all changes on staging environment first
  ```bash
  # On staging server
  git pull origin staging
  pip install -r requirements.txt
  python verify_migration.py
  # Run smoke tests...
  ```
  - Test result: [ ] PASS [ ] FAIL
  - Issues found: ________________________________________

- [ ] **Prepare Rollback Plan** - Know how to revert if needed
  - Previous good backup location: ________________
  - Quick rollback steps documented: [ ] Yes [ ] No
  - Estimated rollback time: _______ minutes

---

## 🔒 Backup Phase (1-2 Hours Before)

### Database Backup

- [ ] **Create Full Backup**
  ```bash
  python backup_database.py
  # Creates timestamped backup in backups/ directory
  ```
  - Backup file created: ________________________________
  - File size: __________________________ MB
  - Backup verified: [ ] Yes [ ] No

- [ ] **Verify Backup Integrity**
  ```bash
  python backup_database.py --verify backups/store.db.backup.TIMESTAMP
  # Should show: "✓ Backup database integrity verified"
  ```
  - Verification result: [ ] PASS [ ] FAIL
  - If FAIL, create new backup and retry

- [ ] **Secondary Backup** - Copy to external location
  ```bash
  # Option A: Copy to external drive/NAS
  cp backups/store.db.backup.LATEST /mnt/external/backup/
  
  # Option B: Copy to cloud storage
  aws s3 cp backups/store.db.backup.LATEST s3://your-bucket/backups/
  ```
  - Secondary backup created: [ ] Yes [ ] No
  - Location: ________________________________________

- [ ] **Record Backup Details** in deployment log
  - Primary backup: ________________________________
  - Secondary backup: ________________________________
  - Backup timestamp: ________________________________
  - Pre-deployment row counts recorded: [ ] Yes [ ] No

### Document Current State

- [ ] **Record Data Counts** before changes
  ```bash
  python -c "
  import sqlite3
  conn = sqlite3.connect('store.db')
  tables = ['products', 'orders', 'users', 'regions']
  for t in tables:
      count = conn.execute(f'SELECT COUNT(*) FROM {t}').fetchone()[0]
      print(f'{t}: {count}')
  "
  ```
  - Products: ____________
  - Orders: ____________
  - Users: ____________
  - Regions: ____________

---

## 🚀 Deployment Phase (During Maintenance Window)

### Code Deployment

- [ ] **Stop Application** (Optional, if zero-downtime deployment not possible)
  ```bash
  # For Flask apps running in systemd
  sudo systemctl stop grocery_app
  
  # Or if using supervisor
  sudo supervisorctl stop grocery_app
  
  # Note: Only required for non-zero-downtime changes
  ```
  - Status: [ ] Stopped [ ] Running (zero-downtime)
  - Time stopped: ______________

- [ ] **Pull Latest Code**
  ```bash
  cd /path/to/app
  git pull origin main
  # Or: git pull origin production
  ```
  - Branch pulled: ________________
  - Commit hash: ________________
  - Conflicts (if any): _________________________________

- [ ] **Install Dependencies**
  ```bash
  pip install -r requirements.txt
  # (Virtual environment should be activated)
  ```
  - All packages installed: [ ] Yes [ ] No
  - Error messages: _________________________________

- [ ] **Run Migrations** (if database schema changed)
  ```bash
  # Migrations run automatically on app startup if needed
  # Or manually trigger with:
  # python -c "from app import init_db; init_db()"
  ```
  - Migrations applied: [ ] Yes [ ] No [ ] N/A
  - Migration log: _________________________________

- [ ] **Restart Application**
  ```bash
  # For systemd
  sudo systemctl start grocery_app
  sudo systemctl status grocery_app
  
  # Or for supervisor
  sudo supervisorctl start grocery_app
  ```
  - App started successfully: [ ] Yes [ ] No
  - Startup time: ______________ seconds

---

## ✅ Verification Phase (Immediately After Deployment)

### Database Integrity Checks

- [ ] **Run Verification Script**
  ```bash
  python verify_migration.py
  ```
  - Overall status: [ ] PASS [ ] FAIL
  - All checks passed: [ ] Yes [ ] No
  - Failed checks: _________________________________

- [ ] **Compare Data Counts** (should match pre-deployment)
  ```bash
  python -c "
  import sqlite3
  conn = sqlite3.connect('store.db')
  tables = ['products', 'orders', 'users', 'regions']
  for t in tables:
      count = conn.execute(f'SELECT COUNT(*) FROM {t}').fetchone()[0]
      print(f'{t}: {count}')
  "
  ```
  - Products: ____________ (was ____________)
  - Orders: ____________ (was ____________)
  - Users: ____________ (was ____________)
  - Regions: ____________ (was ____________)
  - All counts match: [ ] Yes [ ] No

- [ ] **Check Migration Versions**
  ```bash
  python -c "
  import sqlite3
  conn = sqlite3.connect('store.db')
  migrations = conn.execute(
      'SELECT version, description FROM schema_version ORDER BY version'
  ).fetchall()
  for v, d in migrations:
      print(f'v{v}: {d}')
  "
  ```
  - Expected versions applied: [ ] Yes [ ] No
  - Versions: _________________________________

### Application Functionality Checks

- [ ] **Manual Smoke Tests**
  ```
  [ ] Homepage loads without errors
  [ ] Product listing shows all items
  [ ] Search functionality works
  [ ] Cart operations work
  [ ] Checkout process works
  [ ] Admin login works
  [ ] Admin can manage products
  [ ] Admin can view orders
  ```

- [ ] **Check Logs for Errors**
  ```bash
  tail -100 /var/log/grocery_app/app.log | grep -i error
  tail -50 /var/log/grocery_app/error.log
  ```
  - Critical errors: [ ] None [ ] Some
  - If some, details: _________________________________

- [ ] **Monitor Error Rate** for 10 minutes
  - Check application error tracking (Sentry, DataDog, etc.)
  - Error rate elevated: [ ] Yes [ ] No
  - New errors appeared: [ ] Yes [ ] No

- [ ] **Performance Check** (if applicable)
  ```bash
  # Check database query time
  # Check page load time
  # Check API response time
  ```
  - Performance acceptable: [ ] Yes [ ] No
  - Slow queries: _________________________________

---

## 📊 Monitoring Phase (Next 24 Hours)

### During First Hour (Critical)

- [ ] **Active Monitoring**
  ```bash
  # Keep terminal open watching logs
  tail -f /var/log/grocery_app/app.log
  
  # Monitor CPU and memory
  watch -n 5 'ps aux | grep python'
  ```
  - Monitoring started at: ______________
  - Resources: CPU ___% | Memory ___% | Disk ___GB

- [ ] **Customer Activity Check**
  - [ ] Can users place orders?
  - [ ] Are orders being processed?
  - [ ] Payment gateway working?
  - [ ] Notifications sending?

- [ ] **Database Health**
  - [ ] Database responding quickly?
  - [ ] No locks or timeouts?
  - [ ] Backup size normal?

### During First 24 Hours (Ongoing)

- [ ] **Hourly Spot Checks**
  - [ ] 1 hour: App status OK
  - [ ] 4 hours: App status OK
  - [ ] 8 hours: App status OK
  - [ ] 24 hours: App status OK

- [ ] **Monitor Error Rates** (if using APM)
  - Error rate normal: [ ] Yes [ ] No
  - Response times normal: [ ] Yes [ ] No
  - Database performance normal: [ ] Yes [ ] No

- [ ] **Customer Reports**
  - Any reported issues: [ ] Yes [ ] No
  - Issues: _________________________________

---

## 🚨 Rollback Phase (Only If Problems)

**Only execute if critical issues found and cannot be resolved quickly**

### Quick Rollback (< 5 minutes)

- [ ] **Stop Application**
  ```bash
  sudo systemctl stop grocery_app
  ```

- [ ] **Restore Backup**
  ```bash
  # Restore primary backup
  cp backups/store.db.backup.TIMESTAMP store.db
  
  # Or restore from secondary backup
  # cp /mnt/external/backup/store.db.backup.TIMESTAMP store.db
  ```
  - Backup restored: __________________________________
  - File verified: [ ] Yes [ ] No

- [ ] **Revert Code** (if code caused issue)
  ```bash
  git revert HEAD
  # Or: git checkout previous_commit
  ```
  - Code reverted to: ________________________________

- [ ] **Restart Application**
  ```bash
  sudo systemctl start grocery_app
  sudo systemctl status grocery_app
  ```

- [ ] **Verify Rollback**
  ```bash
  python verify_migration.py
  ```
  - Rollback verified: [ ] Yes [ ] No
  - Status: [ ] PASS [ ] FAIL

- [ ] **Notify Stakeholders**
  - [ ] Team notified
  - [ ] Reason documented: _____________________________

### Deep Dive Debugging (If needed)

- [ ] **Collect Diagnostics**
  ```bash
  # Get recent logs
  tail -200 /var/log/grocery_app/app.log > deployment_issue_logs.txt
  
  # Get database state
  python verify_migration.py --report issue_report.json
  
  # Get system state
  uname -a > system_info.txt
  python --version >> system_info.txt
  ```

- [ ] **Review Database State**
  - Check if data is intact
  - Check if schema matches expectations
  - Run queries to verify data consistency

- [ ] **Post-Mortem**
  - What went wrong: _________________________________
  - Root cause: _________________________________
  - How to prevent: _________________________________

---

## ✨ Post-Deployment Phase (After Verification)

### Documentation

- [ ] **Update CHANGELOG**
  - Version deployed: ________________
  - Date/time: ________________
  - Changes made: _________________________________
  - Result: [ ] SUCCESS [ ] FAILED

- [ ] **Archive Deployment Notes**
  - Create file: `deployment_YYYYMMDD_HHMM.log`
  - Include: backup location, data counts, verification results
  - Location: ________________________________________

- [ ] **Cleanup Old Backups** (after 7 days of stability)
  ```bash
  python backup_database.py --cleanup-only --days 14
  ```

### Team Communication

- [ ] **Send Deployment Summary**
  - To: ________________________________
  - Include: changes made, verification results, any issues
  - Status: [ ] Sent

- [ ] **Celebrate!** 🎉
  - Deployment successful: [ ] Yes [ ] No
  - Team acknowledged: [ ] Yes [ ] No

---

## 📋 Deployment Quick Reference

### Essential Commands

```bash
# 1. Create backup
python backup_database.py

# 2. Verify current state
python verify_migration.py

# 3. Deploy code
git pull origin main

# 4. Restart app
sudo systemctl restart grocery_app

# 5. Verify deployment
python verify_migration.py

# 6. Check data counts
python -c "import sqlite3; conn = sqlite3.connect('store.db'); ..."

# 7. Cleanup
python backup_database.py --cleanup-only
```

### Emergency Rollback

```bash
# Stop app
sudo systemctl stop grocery_app

# Restore backup
cp backups/store.db.backup.TIMESTAMP store.db

# Revert code
git revert HEAD

# Restart app
sudo systemctl start grocery_app

# Verify
python verify_migration.py
```

---

## 📞 Support Contacts

| Role | Name | Contact | Available |
|------|------|---------|-----------|
| DevOps | _________________ | _________________ | [ ] Yes [ ] No |
| Database Admin | _________________ | _________________ | [ ] Yes [ ] No |
| Lead Developer | _________________ | _________________ | [ ] Yes [ ] No |
| Tech Lead | _________________ | _________________ | [ ] Yes [ ] No |

---

## ✍️ Deployment Sign-Off

By signing below, I confirm that this deployment has been completed successfully with all checks passed.

**Deployed By**: _________________ **Date**: _________________ **Time**: _________________

**Verified By**: _________________ **Date**: _________________ **Time**: _________________

**Backup Location**: _________________________________________________________________

**Issues Encountered**: ________________________________________________________________

**Resolution**: _____________________________________________________________________

---

## 📚 Related Documentation

- **DATABASE_MIGRATION_GUIDE.md** - Complete migration best practices
- **PRODUCTION_MIGRATION_IMPLEMENTATION.md** - App-specific implementation
- **DATABASE_SAFETY_QUICK_REFERENCE.md** - Quick answers about data safety
- **MIGRATION_DECISION_TREE.md** - How to choose migration strategies

---

**Last Deployment**: _______________  
**Next Scheduled Check**: _______________  
**Status**: [ ] Ready for Production [ ] Needs Review


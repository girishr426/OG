# 🚀 Production Safety Tools - Quick Reference

**Status**: ✅ All systems implemented and tested  
**Last Verified**: December 22, 2025  

---

## 📦 What You Have

5 production-grade tools to keep your database safe:

| Tool | File | Command | Purpose |
|------|------|---------|---------|
| **Backup** | `backup_database.py` | `python backup_database.py` | Create timestamped backups |
| **Verify** | `verify_migration.py` | `python verify_migration.py` | Check database health |
| **Migrate** | `migration_helper.py` | `from migration_helper import Migration` | Create safe schema changes |
| **Deploy** | `DEPLOYMENT_CHECKLIST.md` | Follow the 7 phases | Safe production deployment |
| **Track** | `app.py` schema_version table | Auto-tracked | All migrations recorded |

---

## ⚡ One-Line Commands

### Create Backup
```bash
python backup_database.py
```
✅ Creates: `backups/store.db.backup.20251222_213657`

### Verify Database
```bash
python verify_migration.py --quiet
```
✅ Output: `✓ PASS - 7/7 checks passed`

### List All Backups
```bash
python backup_database.py --list
```
✅ Shows: File size, age, timestamps

### Quick Health Check
```bash
python -c "import sqlite3; c=sqlite3.connect('store.db'); print('✓ DB OK' if c.execute('PRAGMA integrity_check').fetchone()[0]=='ok' else '✗ DB ERROR')"
```

---

## 🛡️ Before Any Deployment

**Step 1: Backup** (2 minutes)
```bash
python backup_database.py
```

**Step 2: Verify** (1 minute)
```bash
python verify_migration.py --quiet
```

**Step 3: Deploy Code** (varies)
```bash
git pull origin main
```

**Step 4: Verify Again** (1 minute)
```bash
python verify_migration.py --quiet
```

---

## 🚨 Emergency Rollback

**Stop the app**
```bash
sudo systemctl stop grocery_app
```

**Restore latest backup**
```bash
cp backups/store.db.backup.LATEST store.db
```

**Restart the app**
```bash
sudo systemctl start grocery_app
```

**Verify rollback**
```bash
python verify_migration.py
```

---

## 📝 For Schema Changes

### Simple Column Add

```python
# 1. Define migration
from migration_helper import Migration

v6 = Migration(
    version=6,
    description='Add discount column',
    up='ALTER TABLE products ADD COLUMN discount REAL DEFAULT 0'
)

# 2. Apply
from migration_helper import run_migrations
run_migrations([v6])

# 3. Verify
python verify_migration.py
```

### Complex Changes

```python
# 1. Create callback function
def migrate_up(conn):
    cur = conn.cursor()
    cur.execute('ALTER TABLE orders ADD COLUMN status TEXT')
    cur.execute('UPDATE orders SET status = "pending"')
    conn.commit()

# 2. Define migration
from migration_helper import Migration

v7 = Migration(
    version=7,
    description='Add status column to orders',
    up_func=migrate_up
)

# 3. Apply and verify
from migration_helper import run_migrations
run_migrations([v7])
python verify_migration.py
```

---

## 📊 Check Current State

### Data Counts
```bash
python -c "
import sqlite3
c = sqlite3.connect('store.db')
for t in ['products', 'orders', 'users', 'regions']:
    count = c.execute(f'SELECT COUNT(*) FROM {t}').fetchone()[0]
    print(f'{t}: {count}')
"
```

### Migration History
```bash
python -c "
import sqlite3
c = sqlite3.connect('store.db')
rows = c.execute('SELECT version, description FROM schema_version ORDER BY version').fetchall()
for v, d in rows:
    print(f'v{v}: {d}')
"
```

### Database Size
```bash
ls -lh store.db
# or on Windows: dir store.db
```

---

## 🗂️ File Locations

```
grocery_store_flask_razorpay/
├── app.py                          ✅ Schema version tracking added
├── backup_database.py              ✅ Backup utility (NEW)
├── verify_migration.py             ✅ Verification tool (NEW)
├── migration_helper.py             ✅ Migration framework (NEW)
├── DEPLOYMENT_CHECKLIST.md         ✅ Deployment guide (NEW)
├── store.db                        📦 Your database
└── backups/                        📁 Auto-created
    └── store.db.backup.20251222_213657  Latest backup
```

---

## ✅ Verification Checklist

- [ ] Can create backup: `python backup_database.py` ✓
- [ ] Can verify: `python verify_migration.py --quiet` ✓
- [ ] Backup size reasonable (< 1 MB for now)
- [ ] All 7 checks pass in verification
- [ ] Data counts make sense (8 products, 30 regions)
- [ ] App starts without errors
- [ ] No foreign key violations

---

## 🎓 Common Scenarios

### "I want to add a new column to products"
1. Create migration v6 using `migration_helper.py`
2. Test on development copy first
3. Run `python verify_migration.py` to confirm
4. Follow `DEPLOYMENT_CHECKLIST.md` for production

### "I need to rollback the last deployment"
1. `sudo systemctl stop grocery_app`
2. `cp backups/store.db.backup.PREVIOUS store.db`
3. `sudo systemctl start grocery_app`
4. `python verify_migration.py` to confirm

### "What changed in the last migration?"
```bash
python -c "
import sqlite3
c = sqlite3.connect('store.db')
c.row_factory = sqlite3.Row
for row in c.execute('SELECT * FROM schema_version ORDER BY version DESC LIMIT 1'):
    print(f'Latest: v{row[\"version\"]} - {row[\"description\"]}')
    print(f'Applied: {row[\"applied_at\"]}')
"
```

### "I'm deploying to production"
1. Read: `DEPLOYMENT_CHECKLIST.md`
2. Follow all 7 phases
3. Get backup location ready
4. Have team on standby
5. Execute checklist step-by-step

---

## 🔧 Troubleshooting

### "Database locked error"
```bash
# Kill any open connections
python -c "import sqlite3; c=sqlite3.connect('store.db'); c.close()"

# Try again
python verify_migration.py
```

### "Backup verification failed"
```bash
# Create new backup
python backup_database.py

# Verify it
python backup_database.py --verify backups/store.db.backup.LATEST
```

### "Migration didn't apply"
```bash
# Check what was applied
python -c "
import sqlite3
c = sqlite3.connect('store.db')
versions = c.execute('SELECT version FROM schema_version').fetchall()
print(f'Applied versions: {[v[0] for v in versions]}')
"

# Check logs
tail -50 app.log
```

---

## 📞 Who to Contact If...

| Issue | Action |
|-------|--------|
| Database won't start | Check `verify_migration.py` output |
| Backup failed | Check disk space, file permissions |
| Schema migration stuck | Check `app.log` for detailed error |
| Data looks wrong | Restore backup from before change |
| Unsure about deployment | Follow `DEPLOYMENT_CHECKLIST.md` |

---

## 🎯 Remember

```
✅ Always backup BEFORE deployment
✅ Always verify AFTER deployment
✅ Keep backups for at least 7 days
✅ Document any manual schema changes
✅ Test migrations on copy first
✅ Have rollback plan ready
✅ Notify team before production changes
```

---

## 📚 Complete Guides

For detailed information, see:
- `DATABASE_MIGRATION_GUIDE.md` - Everything about migrations
- `PRODUCTION_MIGRATION_IMPLEMENTATION.md` - App-specific details
- `DEPLOYMENT_CHECKLIST.md` - Full deployment procedure
- `DATABASE_SAFETY_QUICK_REFERENCE.md` - Data safety answers

---

**Last Update**: December 22, 2025  
**Status**: ✅ PRODUCTION READY  
**Confidence**: 🟢 Very High


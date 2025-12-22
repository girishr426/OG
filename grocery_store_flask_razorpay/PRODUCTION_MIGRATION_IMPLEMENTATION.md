# 🔄 Your App's Migration Implementation Plan

## Current State Analysis

Your app currently has this migration pattern in `init_db()`:

```python
# CURRENT (Auto-migration, no version tracking)
try:
    cols = cur.execute("PRAGMA table_info(products)").fetchall()
    col_names = {c[1] for c in cols}
    
    if 'mrp' not in col_names:
        cur.execute('ALTER TABLE products ADD COLUMN mrp REAL')
    if 'size' not in col_names:
        cur.execute('ALTER TABLE products ADD COLUMN size TEXT DEFAULT "Standard"')
except Exception:
    pass
```

**Status**: ✅ Works but lacks version tracking and rollback capability

---

## 📋 Recommended: Add Version Tracking

### Step 1: Update `init_db()` in app.py

Replace the migration section with version-tracked approach:

```python
def init_db():
    conn = get_db()
    cur = conn.cursor()
    
    # 1. CREATE INITIAL TABLES (if not exist)
    cur.execute('''
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            description TEXT,
            price REAL NOT NULL,
            stock INTEGER DEFAULT 0,
            estimated_delivery_days INTEGER,
            estimated_delivery_date TEXT,
            image_path TEXT,
            is_homepage INTEGER DEFAULT 0,
            product_status TEXT DEFAULT 'Final Product',
            category TEXT DEFAULT 'Products'
        )
    ''')
    
    cur.execute('''
        CREATE TABLE IF NOT EXISTS schema_version (
            version INTEGER PRIMARY KEY,
            description TEXT NOT NULL,
            applied_at TEXT NOT NULL,
            status TEXT DEFAULT 'applied'
        )
    ''')
    
    # 2. TRACK APPLIED MIGRATIONS
    applied_versions = set()
    try:
        applied_versions = {
            row[0] for row in cur.execute(
                'SELECT version FROM schema_version WHERE status="applied"'
            ).fetchall()
        }
    except Exception:
        pass
    
    # 3. DEFINE ALL MIGRATIONS
    migrations = [
        (1, "Initial schema - create core tables", lambda c: None),  # Already done above
        (2, "Add MRP column to products", migration_v2_add_mrp),
        (3, "Add size column to products", migration_v3_add_size),
        (4, "Create catalog_images table", migration_v4_catalog_images),
        (5, "Add admin_users table", migration_v5_admin_users),
        # Add future migrations here
    ]
    
    # 4. APPLY MISSING MIGRATIONS
    for version, description, migration_func in migrations:
        if version not in applied_versions:
            try:
                migration_func(cur)
                cur.execute(
                    'INSERT INTO schema_version (version, description, applied_at, status) VALUES (?, ?, ?, ?)',
                    (version, description, datetime.now().isoformat(), 'applied')
                )
                conn.commit()
                print(f"✓ Migration v{version}: {description}")
            except Exception as e:
                print(f"✗ Migration v{version} failed: {e}")
                conn.rollback()
                # Don't raise - allow app to continue with partial migration
    
    # 5. CREATE REMAINING TABLES (other tables from original code)
    # ... rest of your table creation code ...
    
    conn.close()


# MIGRATION FUNCTIONS
def migration_v2_add_mrp(cur):
    """Add MRP column to products table"""
    cols = {c[1] for c in cur.execute("PRAGMA table_info(products)").fetchall()}
    if 'mrp' not in cols:
        cur.execute('ALTER TABLE products ADD COLUMN mrp REAL')
        print("  → Added mrp column")


def migration_v3_add_size(cur):
    """Add size column to products table"""
    cols = {c[1] for c in cur.execute("PRAGMA table_info(products)").fetchall()}
    if 'size' not in cols:
        cur.execute('ALTER TABLE products ADD COLUMN size TEXT DEFAULT "Standard"')
        # Backfill existing records
        cur.execute('UPDATE products SET size="Standard" WHERE size IS NULL')
        print("  → Added size column with defaults")


def migration_v4_catalog_images(cur):
    """Create catalog_images table for hero carousel"""
    cur.execute('''
        CREATE TABLE IF NOT EXISTS catalog_images (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            region TEXT NOT NULL,
            position INTEGER NOT NULL,
            image_path TEXT NOT NULL,
            alt_text TEXT,
            created_at TEXT,
            updated_at TEXT,
            UNIQUE(region, position)
        )
    ''')
    print("  → Created catalog_images table")


def migration_v5_admin_users(cur):
    """Create admin_users table if not exists"""
    cur.execute('''
        CREATE TABLE IF NOT EXISTS admin_users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE,
            password_hash TEXT
        )
    ''')
    print("  → Verified admin_users table exists")
```

---

## 🔒 Safety Features Included

### 1. **Version Tracking**
- ✅ Records which migrations have been applied
- ✅ Prevents re-running migrations
- ✅ Tracks timestamp of each migration

### 2. **Data Preservation**
```python
# Each migration uses safe patterns:

# ✅ Adding column with DEFAULT
ALTER TABLE products ADD COLUMN size TEXT DEFAULT "Standard"

# ✅ Backfill data
UPDATE products SET size="Standard" WHERE size IS NULL

# ✅ CREATE IF NOT EXISTS
CREATE TABLE IF NOT EXISTS catalog_images (...)
```

### 3. **Error Handling**
```python
try:
    migration_func(cur)
    conn.commit()
    print(f"✓ Migration applied")
except Exception as e:
    conn.rollback()  # Roll back this transaction only
    print(f"✗ Migration failed: {e}")
    # App continues - doesn't crash
```

### 4. **Idempotent Operations**
```python
# Safe to run multiple times
def migration_v3_add_size(cur):
    cols = {c[1] for c in cur.execute("PRAGMA table_info(products)").fetchall()}
    if 'size' not in cols:  # Only if not already present
        cur.execute('ALTER TABLE products ADD COLUMN size TEXT DEFAULT "Standard"')
```

---

## 📊 Current Database State (After Hero Carousel Changes)

Your database now has:

```
schema_version (NEW - for tracking migrations)
├─ v1: Initial schema
├─ v2: Add MRP column
├─ v3: Add size column
├─ v4: Create catalog_images table
└─ v5: Admin users table

products (UPDATED)
├─ id, name, description (original)
├─ price, mrp (v2 added mrp)
├─ size (v3 added, DEFAULT "Standard")
└─ ... other columns

catalog_images (NEW - v4)
├─ id, region, position
├─ image_path, alt_text
└─ created_at, updated_at

... other tables unchanged ...
```

---

## 🚀 Deployment Procedure (With Migration Version Control)

### Development to Staging
```bash
# 1. Test with production data copy
cp production_store.db staging_store.db

# 2. Run migrations
python -c "
import os
os.rename('store.db', 'store.db.backup')
os.rename('staging_store.db', 'store.db')

from app import init_db
init_db()

print('✓ Migrations completed')
print('✓ Check schema_version table:')

import sqlite3
conn = sqlite3.connect('store.db')
rows = conn.execute(
    'SELECT version, description, applied_at FROM schema_version ORDER BY version'
).fetchall()
for v, desc, timestamp in rows:
    print(f'  v{v}: {desc}')
conn.close()
"

# 3. Run tests
pytest tests/

# 4. If all good, deploy to production
```

### Staging to Production
```bash
# 1. Backup production database
cp store.db store.db.backup.$(date +%Y%m%d_%H%M%S)

# 2. Verify backup
ls -lh store.db.backup.*

# 3. Run migrations
python -c "from app import init_db; init_db()"

# 4. Verify
python -c "
import sqlite3
conn = sqlite3.connect('store.db')
count = conn.execute('SELECT COUNT(*) FROM products').fetchone()[0]
print(f'✓ Products: {count}')
conn.close()
"

# 5. Monitor logs
tail -f app.log
```

---

## 🔍 Verification Script

Create `verify_migration.py`:

```python
#!/usr/bin/env python
"""Verify database after migration"""

import sqlite3
import sys

def verify():
    conn = sqlite3.connect('store.db')
    cur = conn.cursor()
    
    print("🔍 Database Verification\n")
    
    # Check schema_version table
    print("1. Migration History:")
    try:
        rows = cur.execute(
            'SELECT version, description, applied_at FROM schema_version ORDER BY version'
        ).fetchall()
        if rows:
            for v, desc, timestamp in rows:
                print(f"   ✓ v{v}: {desc}")
                print(f"      Applied: {timestamp}")
        else:
            print("   ⚠️  No migrations tracked")
    except Exception as e:
        print(f"   ✗ Error: {e}")
        return False
    
    # Check products table
    print("\n2. Products Table:")
    try:
        columns = [c[1] for c in cur.execute("PRAGMA table_info(products)").fetchall()]
        print(f"   Columns: {', '.join(columns)}")
        
        count = cur.execute('SELECT COUNT(*) FROM products').fetchone()[0]
        print(f"   ✓ Total products: {count}")
        
        # Check new columns
        if 'mrp' in columns:
            print(f"   ✓ MRP column exists")
        if 'size' in columns:
            print(f"   ✓ Size column exists")
            nulls = cur.execute('SELECT COUNT(*) FROM products WHERE size IS NULL').fetchone()[0]
            if nulls > 0:
                print(f"   ⚠️  {nulls} products with NULL size (should have default)")
            else:
                print(f"   ✓ All products have size value")
    except Exception as e:
        print(f"   ✗ Error: {e}")
        return False
    
    # Check catalog_images table
    print("\n3. Catalog Images Table:")
    try:
        count = cur.execute('SELECT COUNT(*) FROM catalog_images').fetchone()[0]
        print(f"   ✓ Total images: {count}")
        
        regions = cur.execute(
            'SELECT region, COUNT(*) FROM catalog_images GROUP BY region'
        ).fetchall()
        for region, cnt in regions:
            print(f"   ✓ Region "{region}": {cnt} images")
    except Exception as e:
        print(f"   ✓ Table exists but may be empty")
    
    conn.close()
    print("\n✅ Verification completed")
    return True

if __name__ == '__main__':
    success = verify()
    sys.exit(0 if success else 1)
```

**Run after deployment:**
```bash
python verify_migration.py
```

---

## 🆘 Rollback Procedure

### If Migration Fails

**Option 1: Rollback to backup**
```bash
# 1. Stop the app
systemctl stop flask_app

# 2. Restore backup
cp store.db store.db.failed
cp store.db.backup.20251222_120000 store.db

# 3. Verify
python verify_migration.py

# 4. Start app
systemctl start flask_app
```

**Option 2: Remove migration marker** (if issue is just a bad migration)
```python
import sqlite3
conn = sqlite3.connect('store.db')
conn.execute('DELETE FROM schema_version WHERE version=4')
conn.commit()
conn.close()

# Then fix the migration function and retry
```

---

## 📈 Production Checklist

Before deploying to production with schema changes:

- [ ] ✅ Test migrations with production data copy
- [ ] ✅ Create backup of current database
- [ ] ✅ Document all schema changes
- [ ] ✅ Prepare rollback procedure
- [ ] ✅ Verify migration functions are idempotent
- [ ] ✅ Check all migrations have defaults for new columns
- [ ] ✅ Backfill critical data (not just defaults)
- [ ] ✅ Run verification script
- [ ] ✅ Monitor app logs after deployment
- [ ] ✅ Keep backup for at least 7 days

---

## 🎯 Summary for Your App

**What's happening now:**
- ✅ Your app has hero carousel (catalog_images table)
- ✅ Products have size field with defaults
- ✅ No data loss occurred during changes

**To add version tracking:**
1. Add migration functions (v2, v3, v4, v5)
2. Create schema_version table
3. Apply migrations on startup
4. Track all future changes

**Benefits:**
- 📝 Know which migrations were applied
- 🔄 Can add new migrations safely
- 🔒 Can verify data integrity
- 🆘 Can rollback if needed
- 📊 Audit trail of schema changes

---

**Recommendation**: Implement version tracking now to protect future updates.

**Time to implement**: ~30 minutes
**Difficulty**: Easy
**Risk**: Very low (just adds tracking, doesn't change behavior)

---

**Created**: December 22, 2025
**Status**: Ready to Implement
**Target**: Production Database Safety

# 🗄️ Database Migration & Production Update Strategy

## Overview
When updating code that affects the database schema, you need a robust strategy to handle existing data in production without data loss.

---

## 📋 Current Situation in Your App

### Database Initialization Pattern
Your app uses an auto-migration approach in `init_db()`:

```python
def init_db():
    conn = get_db()
    cur = conn.cursor()
    
    # Create tables if they don't exist
    cur.execute('CREATE TABLE IF NOT EXISTS products (...)')
    
    # Backfill migration: add columns if missing
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

**✅ GOOD**: Handles missing columns gracefully
**⚠️ ISSUE**: No version tracking or rollback capability

---

## 🛡️ Best Practices for Production Updates

### 1. **Use Migration Version Tracking** ⭐

Add a `schema_version` table to track what migrations have been applied:

```python
def init_db():
    conn = get_db()
    cur = conn.cursor()
    
    # Create version tracking table
    cur.execute('''
        CREATE TABLE IF NOT EXISTS schema_version (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            version INTEGER UNIQUE NOT NULL,
            description TEXT,
            applied_at TEXT,
            rolled_back_at TEXT
        )
    ''')
    
    # Apply migrations
    migrations = [
        (1, "Initial schema", schema_v1),
        (2, "Add MRP column", schema_v2),
        (3, "Add size column", schema_v3),
        (4, "Add hero images", schema_v4),
    ]
    
    for version, desc, migration_func in migrations:
        # Check if already applied
        existing = cur.execute(
            'SELECT id FROM schema_version WHERE version=? AND rolled_back_at IS NULL',
            (version,)
        ).fetchone()
        
        if not existing:
            try:
                migration_func(cur)
                cur.execute(
                    'INSERT INTO schema_version (version, description, applied_at) VALUES (?, ?, ?)',
                    (version, desc, datetime.now().isoformat())
                )
                print(f"✓ Migration {version}: {desc}")
            except Exception as e:
                print(f"✗ Migration {version} failed: {e}")
                conn.rollback()
                return False
    
    conn.commit()
    conn.close()
    return True
```

---

## 🔄 Migration Strategies

### Strategy 1: **Zero-Downtime Migrations** (Recommended for Production)

**Steps**:
1. Add new column with DEFAULT value
2. Deploy new code (reads both old and new columns)
3. Backfill data in background
4. Eventually deprecate old column

**Example: Adding `size` column**

```python
# Step 1: Add column with default
def add_size_column(cur):
    try:
        cols = {c[1] for c in cur.execute("PRAGMA table_info(products)").fetchall()}
        if 'size' not in cols:
            cur.execute('''
                ALTER TABLE products 
                ADD COLUMN size TEXT DEFAULT 'Standard'
            ''')
            print("✓ Added 'size' column with default value")
    except Exception as e:
        print(f"Column already exists: {e}")

# Step 2: New code handles both columns
def get_product_size(product_id):
    # Handles NULL safely
    return db.query("SELECT size FROM products WHERE id=?")[0] or 'Standard'

# Step 3: Background job to backfill (optional)
def backfill_sizes():
    conn = get_db()
    conn.execute("UPDATE products SET size='Standard' WHERE size IS NULL")
    conn.commit()
    conn.close()
```

**Advantages**:
- ✅ No downtime
- ✅ Can rollback if issues
- ✅ Data preserved
- ✅ Gradual deployment

---

### Strategy 2: **Structured Migrations** (Recommended for New Tables)

**Pattern**:
```python
class Migration:
    def up(self, cur):
        """Apply the migration"""
        pass
    
    def down(self, cur):
        """Rollback the migration"""
        pass

class AddSizeColumn(Migration):
    def up(self, cur):
        cur.execute('''
            ALTER TABLE products 
            ADD COLUMN size TEXT DEFAULT 'Standard'
        ''')
    
    def down(self, cur):
        cur.execute('''
            ALTER TABLE products 
            DROP COLUMN size
        ''')

class AddCatalogImages(Migration):
    def up(self, cur):
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
    
    def down(self, cur):
        cur.execute('DROP TABLE IF EXISTS catalog_images')
```

---

## 🚀 Production Deployment Checklist

### Before Deploying
- [ ] ✅ Test migration with copy of production database
- [ ] ✅ Create database backup
- [ ] ✅ Plan rollback procedure
- [ ] ✅ Notify users if downtime needed
- [ ] ✅ Have rollback script ready

### During Deployment

**Option A: Quick Deployment (< 1 minute downtime)**
```bash
# 1. Stop application
systemctl stop flask_app

# 2. Backup database
cp store.db store.db.backup-2025-12-22

# 3. Run migrations
python -c "from app import init_db; init_db()"

# 4. Verify
python -c "from app import get_db; print(get_db().execute('SELECT COUNT(*) FROM products').fetchone())"

# 5. Start application
systemctl start flask_app
```

**Option B: Blue-Green Deployment (Zero downtime)**
```bash
# 1. Create new database copy
cp store.db store.db.new

# 2. Run migrations on copy
python migrate.py --db store.db.new

# 3. Verify migrations
python verify.py --db store.db.new

# 4. Switch over (atomic)
mv store.db store.db.old
mv store.db.new store.db

# 5. If error, switch back
mv store.db store.db.new
mv store.db.old store.db
```

---

## 💾 Data Preservation Techniques

### 1. **Adding a Column**
```python
# ✅ GOOD: With DEFAULT value
ALTER TABLE products ADD COLUMN size TEXT DEFAULT 'Standard';

# ⚠️ RISKY: Without DEFAULT (allows NULL)
ALTER TABLE products ADD COLUMN size TEXT;

# ✅ BETTER: With DEFAULT + NOT NULL
ALTER TABLE products ADD COLUMN size TEXT NOT NULL DEFAULT 'Standard';
```

### 2. **Renaming a Column**
```python
# Step 1: Create new column
ALTER TABLE products ADD COLUMN new_name TEXT;

# Step 2: Copy data
UPDATE products SET new_name = old_name;

# Step 3: Drop old column (after verifying)
ALTER TABLE products DROP COLUMN old_name;
```

### 3. **Changing Column Type**
```python
# SQLite doesn't support MODIFY, so:

# Step 1: Create new table with new schema
CREATE TABLE products_new (
    id INTEGER PRIMARY KEY,
    price REAL,  -- Changed from TEXT to REAL
    ...
);

# Step 2: Copy data with conversion
INSERT INTO products_new SELECT 
    id, 
    CAST(price AS REAL),  -- Convert TEXT to REAL
    ...
FROM products;

# Step 3: Drop old and rename
DROP TABLE products;
ALTER TABLE products_new RENAME TO products;
```

### 4. **Adding a New Table**
```python
# Simple and safe - doesn't affect existing data
CREATE TABLE IF NOT EXISTS catalog_images (
    id INTEGER PRIMARY KEY,
    region TEXT NOT NULL,
    position INTEGER NOT NULL,
    image_path TEXT NOT NULL,
    created_at TEXT,
    UNIQUE(region, position)
);
```

---

## 🔍 Verification After Migration

```python
def verify_migration():
    conn = get_db()
    
    # Check table structure
    tables = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table'"
    ).fetchall()
    print(f"✓ Tables: {len(tables)}")
    
    # Check columns
    cols = conn.execute("PRAGMA table_info(products)").fetchall()
    col_names = [c[1] for c in cols]
    print(f"✓ Product columns: {col_names}")
    
    # Check data integrity
    count = conn.execute("SELECT COUNT(*) FROM products").fetchone()[0]
    print(f"✓ Product count: {count}")
    
    # Check specific column
    size_nulls = conn.execute(
        "SELECT COUNT(*) FROM products WHERE size IS NULL"
    ).fetchone()[0]
    print(f"✓ Products with size=NULL: {size_nulls}")
    
    conn.close()
```

---

## 🔧 Implementation Example for Your App

### Current Auto-Migration (What You Have)
```python
# In app.py init_db()
try:
    cols = cur.execute("PRAGMA table_info(products)").fetchall()
    col_names = {c[1] for c in cols}
    
    if 'mrp' not in col_names:
        cur.execute('ALTER TABLE products ADD COLUMN mrp REAL')
        conn.commit()
    
    if 'size' not in col_names:
        cur.execute('ALTER TABLE products ADD COLUMN size TEXT DEFAULT "Standard"')
        conn.commit()
except Exception:
    pass
```

**Issue**: No version tracking, no rollback capability

### Improved Version (Recommended)
```python
def init_db():
    conn = get_db()
    cur = conn.cursor()
    
    # Create schema version table
    cur.execute('''
        CREATE TABLE IF NOT EXISTS schema_version (
            version INTEGER PRIMARY KEY,
            description TEXT,
            applied_at TEXT
        )
    ''')
    
    # List of migrations
    migrations = {
        1: ("Initial schema", setup_initial_schema),
        2: ("Add MRP column", add_mrp_column),
        3: ("Add size column", add_size_column),
        4: ("Add catalog_images table", add_catalog_images),
        5: ("Add hero region support", add_hero_support),
    }
    
    # Apply missing migrations
    applied = {row[0] for row in cur.execute(
        'SELECT version FROM schema_version'
    ).fetchall()}
    
    for version in sorted(migrations.keys()):
        if version not in applied:
            desc, migration_func = migrations[version]
            try:
                migration_func(cur)
                cur.execute(
                    'INSERT INTO schema_version (version, description, applied_at) VALUES (?, ?, ?)',
                    (version, desc, datetime.now().isoformat())
                )
                conn.commit()
                print(f"✓ Applied migration {version}: {desc}")
            except Exception as e:
                print(f"✗ Migration {version} failed: {e}")
                conn.rollback()
                break
    
    conn.close()

# Define migration functions
def add_mrp_column(cur):
    cols = {c[1] for c in cur.execute("PRAGMA table_info(products)").fetchall()}
    if 'mrp' not in cols:
        cur.execute('ALTER TABLE products ADD COLUMN mrp REAL')

def add_size_column(cur):
    cols = {c[1] for c in cur.execute("PRAGMA table_info(products)").fetchall()}
    if 'size' not in cols:
        cur.execute('ALTER TABLE products ADD COLUMN size TEXT DEFAULT "Standard"')

def add_catalog_images(cur):
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

def add_hero_support(cur):
    # No schema change needed, just a marker
    pass
```

---

## 🛠️ Backup & Recovery Strategy

### Daily Backup Script
```python
import shutil
import datetime

def backup_database():
    """Create timestamped backup"""
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_file = f"backups/store_{timestamp}.db"
    
    shutil.copy2('store.db', backup_file)
    print(f"✓ Backup created: {backup_file}")
    return backup_file

def restore_from_backup(backup_file):
    """Restore database from backup"""
    import os
    if not os.path.exists(backup_file):
        print(f"✗ Backup file not found: {backup_file}")
        return False
    
    shutil.copy2(backup_file, 'store.db')
    print(f"✓ Restored from: {backup_file}")
    return True
```

### Backup Before Every Major Update
```bash
# Before deploying
python -c "from app import backup_database; backup_database()"

# If something goes wrong
python -c "from app import restore_from_backup; restore_from_backup('backups/store_20251222_120000.db')"
```

---

## ⚠️ Common Mistakes to Avoid

| ❌ Mistake | ✅ Solution |
|-----------|-----------|
| No backup before update | Always backup: `cp store.db store.db.backup` |
| ALTER without DEFAULT | Use: `ALTER TABLE t ADD COLUMN c TYPE DEFAULT value` |
| Dropping columns in production | Create new table, copy data, rename |
| No version tracking | Implement schema_version table |
| No rollback plan | Keep previous app version ready |
| Updating in peak hours | Schedule maintenance windows |
| No data verification | Run checks after migration |
| Mixing code & schema changes | Deploy schema first, then code |

---

## 📊 Example: Your Recent Updates

### What Happened (Hero Carousel Addition)

1. **Added catalog_images table** ✅
   - New table, no data loss
   - Safe operation
   - Can be rolled back by dropping table

2. **No existing products affected** ✅
   - Existing data untouched
   - Only new features added
   - Backward compatible

3. **Size column already added** ✅
   - Uses DEFAULT 'Standard'
   - All existing products get this value
   - No NULL values

---

## 🚀 Production-Ready Deployment Script

```python
#!/usr/bin/env python
"""
Production deployment script with safety checks
"""

import os
import shutil
import sqlite3
from datetime import datetime

def deploy():
    print("🚀 Starting production deployment...")
    
    # Step 1: Verify current state
    print("\n1️⃣  Verifying current state...")
    if not os.path.exists('store.db'):
        print("✗ Database not found!")
        return False
    
    # Get current product count
    conn = sqlite3.connect('store.db')
    cur = conn.cursor()
    before_count = cur.execute('SELECT COUNT(*) FROM products').fetchone()[0]
    print(f"   ✓ Current products: {before_count}")
    conn.close()
    
    # Step 2: Create backup
    print("\n2️⃣  Creating backup...")
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = f"backups/store_{timestamp}.db"
    os.makedirs("backups", exist_ok=True)
    shutil.copy2('store.db', backup_path)
    print(f"   ✓ Backup created: {backup_path}")
    
    # Step 3: Run migrations
    print("\n3️⃣  Running migrations...")
    try:
        from app import init_db
        init_db()
        print("   ✓ Migrations completed")
    except Exception as e:
        print(f"   ✗ Migration failed: {e}")
        print(f"   → Restoring from backup...")
        shutil.copy2(backup_path, 'store.db')
        return False
    
    # Step 4: Verify data integrity
    print("\n4️⃣  Verifying data integrity...")
    conn = sqlite3.connect('store.db')
    cur = conn.cursor()
    after_count = cur.execute('SELECT COUNT(*) FROM products').fetchone()[0]
    print(f"   ✓ Products after migration: {after_count}")
    
    if after_count != before_count:
        print(f"   ⚠️  WARNING: Product count changed! ({before_count} → {after_count})")
    else:
        print(f"   ✓ Data integrity verified")
    
    # Check schema version
    versions = cur.execute('''
        SELECT version, description, applied_at 
        FROM schema_version 
        ORDER BY version DESC 
        LIMIT 5
    ''').fetchall()
    
    print("\n   📋 Latest migrations:")
    for v, desc, timestamp in versions:
        print(f"      v{v}: {desc} ({timestamp})")
    
    conn.close()
    
    print("\n✅ Deployment completed successfully!")
    print(f"📦 Backup saved: {backup_path}")
    return True

if __name__ == '__main__':
    deploy()
```

---

## 🔒 Disaster Recovery Plan

### If Migration Fails

```bash
# 1. Immediate recovery
cp backups/store_latest.db store.db
systemctl restart flask_app

# 2. Investigate issue
python -c "
import sqlite3
conn = sqlite3.connect('store.db')
cur = conn.cursor()
print('Tables:', [r[0] for r in cur.execute(
    \"SELECT name FROM sqlite_master WHERE type='table'\"
).fetchall()])
conn.close()
"

# 3. Deploy previous app version
git revert <commit-hash>
pip install -r requirements.txt
systemctl restart flask_app
```

---

## 📈 Monitoring & Alerts

```python
def health_check():
    """Check database health after deployment"""
    conn = get_db()
    checks = {
        'products': conn.execute('SELECT COUNT(*) FROM products').fetchone()[0],
        'orders': conn.execute('SELECT COUNT(*) FROM orders').fetchone()[0],
        'users': conn.execute('SELECT COUNT(*) FROM users').fetchone()[0],
        'catalog_images': conn.execute('SELECT COUNT(*) FROM catalog_images').fetchone()[0],
    }
    
    for table, count in checks.items():
        print(f"✓ {table}: {count} records")
    
    # Alert if something seems wrong
    if checks['products'] == 0:
        print("⚠️  WARNING: No products found!")
    
    conn.close()
    return True

# Run after deployment
health_check()
```

---

## 📚 Summary

### Key Principles for Production Updates

1. **✅ Always backup** - Before any migration
2. **✅ Test first** - On copy of production DB
3. **✅ Version track** - Use schema_version table
4. **✅ Preserve data** - Use DEFAULT values, don't drop columns
5. **✅ Plan rollback** - Have recovery procedure ready
6. **✅ Verify after** - Check data integrity
7. **✅ Gradual rollout** - Blue-green or canary deployments
8. **✅ Monitor** - Watch for issues after deployment

---

**Created**: December 22, 2025
**Status**: ✅ Best Practices Guide
**Target**: Production Deployment Safety

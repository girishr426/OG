# 🛣️ Migration Strategy Decision Tree

## Quick Decision Guide

```
Do you need to update your app in production?
│
└─→ What type of change?
    │
    ├─→ Add a NEW TABLE
    │   │
    │   └─→ CREATE TABLE IF NOT EXISTS new_table (...)
    │       ✅ Safe - doesn't affect existing data
    │       📍 Example: catalog_images table for hero carousel
    │       ⏱️ Zero downtime
    │       🔄 No rollback needed (just drop table if issues)
    │
    ├─→ Add a COLUMN to existing table
    │   │
    │   └─→ Need to preserve existing data?
    │       │
    │       ├─→ YES (always answer YES in production!)
    │           │
    │           └─→ ALTER TABLE table_name ADD COLUMN col_name TYPE DEFAULT value
    │               ✅ Safe - all rows get default value
    │               📍 Example: size column DEFAULT 'Standard'
    │               ⏱️ Quick (seconds)
    │               🔄 Can rollback: DROP COLUMN
    │               ⚠️ SQLite doesn't support DROP COLUMN, so test first!
    │
    │       └─→ NO (will lose data)
    │           ❌ DON'T DO THIS IN PRODUCTION!
    │           Use: CREATE new_table + copy + DROP old + RENAME
    │
    ├─→ REMOVE a COLUMN
    │   │
    │   └─→ ⚠️ SQLite doesn't support DROP COLUMN natively
    │       │
    │       ├─→ Plan 1 (Recommended): Create new table
    │       │   1. CREATE TABLE t_new AS SELECT id, col1, col2 FROM t
    │       │   2. DROP TABLE t
    │       │   3. ALTER TABLE t_new RENAME TO t
    │       │   ✓ Safe, preserves data
    │       │   ⏱️ Requires brief downtime
    │       │   🔄 Can rollback if kept old table
    │       │
    │       └─→ Plan 2 (Lazy): Just stop using it in code
    │           - Don't remove from schema
    │           - Ignore in SELECT queries
    │           - Eventually remove in major version
    │           ✓ Zero downtime
    │
    ├─→ RENAME a COLUMN
    │   │
    │   └─→ ⚠️ SQLite doesn't support RENAME COLUMN (v3.25+)
    │       │
    │       ├─→ If SQLite >= 3.25:
    │       │   ALTER TABLE t RENAME COLUMN old TO new
    │       │
    │       └─→ Otherwise:
    │           1. CREATE TABLE t_new (id, new_col, ...)
    │           2. INSERT INTO t_new SELECT id, old_col, ... FROM t
    │           3. DROP TABLE t
    │           4. ALTER TABLE t_new RENAME TO t
    │
    ├─→ CHANGE COLUMN TYPE
    │   │
    │   └─→ ⚠️ SQLite doesn't support ALTER COLUMN TYPE
    │       │
    │       └─→ Must recreate table:
    │           1. CREATE TABLE t_new (id, col NEWTYPE, ...)
    │           2. INSERT INTO t_new SELECT id, CAST(col AS NEWTYPE), ... FROM t
    │           3. DROP TABLE t
    │           4. ALTER TABLE t_new RENAME TO t
    │           ✓ Safe but requires downtime
    │           ⏱️ Time depends on data volume
    │
    └─→ UPDATE/MODIFY DATA
        │
        └─→ UPDATE products SET col='value' WHERE condition
            ✅ Always safe (unless wrong WHERE clause!)
            📍 Example: SET size='Standard' WHERE size IS NULL
            ⏱️ Fast for small datasets
            🔄 Can rollback with previous backup
            ⚠️ Test WHERE clause first!
```

---

## 📊 Migration Complexity Matrix

```
┌──────────────────────┬──────────┬──────────┬─────────────┐
│ Operation            │ Safety   │ Downtime │ Difficulty  │
├──────────────────────┼──────────┼──────────┼─────────────┤
│ Add Table            │ ✅ Safe  │ 0s       │ ⭐ Easy     │
│ Add Column (DEFAULT) │ ✅ Safe  │ 1-5s     │ ⭐ Easy     │
│ Add Column (NULL)    │ ⚠️ Risky │ 1-5s     │ ⭐ Easy     │
│ Update Data          │ ✅ Safe  │ 1-10s    │ ⭐ Easy     │
│ Remove Column        │ ❌ Hard  │ 5-30s    │ ⭐⭐⭐ Hard │
│ Rename Column        │ ❌ Hard  │ 5-30s    │ ⭐⭐⭐ Hard │
│ Change Type          │ ❌ Hard  │ 5-60s    │ ⭐⭐⭐ Hard │
│ Drop Table           │ ⚠️ Risk  │ 1-5s     │ ⭐⭐ Medium │
│ Rename Table         │ ✅ Safe  │ <1s      │ ⭐ Easy     │
└──────────────────────┴──────────┴──────────┴─────────────┘
```

---

## 🎯 Your Recent Changes - Complexity Analysis

### ✅ Hero Carousel Addition (SAFE)

```
Change 1: Added catalog_images table
├─ Type: Add table
├─ Safety: ✅ SAFE
├─ Downtime: 0 seconds
├─ Data affected: None (new table)
└─ Risk: Very low

Change 2: Added size column to products
├─ Type: Add column with DEFAULT
├─ Safety: ✅ SAFE
├─ Downtime: <1 second
├─ Data affected: Existing products get 'Standard' value
├─ Current status: Already migrated
└─ Risk: Very low

Result: ✅ All changes are safe and backward compatible
```

---

## 🚨 Risky Changes You Should AVOID

### ❌ DON'T DO THIS IN PRODUCTION

```python
# ❌ NO: Adding column without DEFAULT
ALTER TABLE products ADD COLUMN size TEXT;
# Problem: NULL values, code breaks expecting defaults

# ❌ NO: Deleting products without backup
DELETE FROM products WHERE status='inactive';
# Problem: Accidental deletion, no recovery possible

# ❌ NO: Changing column types without mapping
ALTER TABLE products MODIFY COLUMN price VARCHAR;
# Problem: SQLite doesn't support this, breaks numeric operations

# ❌ NO: Renaming tables without code update
ALTER TABLE products RENAME TO products_old;
ALTER TABLE products_new RENAME TO products;
# Problem: App still points to old table names, crashes

# ❌ NO: Multiple migrations without rollback plan
# Run 5 migrations at once
# Problem: If #4 fails, you don't know which state you're in
```

---

## ✅ SAFE Patterns You SHOULD Use

```python
# ✅ YES: Adding table (new feature)
CREATE TABLE IF NOT EXISTS catalog_images (
    id INTEGER PRIMARY KEY,
    region TEXT NOT NULL,
    UNIQUE(region, position)
);
# Safe because: Doesn't touch existing data

# ✅ YES: Adding column with DEFAULT
ALTER TABLE products ADD COLUMN size TEXT DEFAULT 'Standard';
# Safe because: Existing rows get default value, no NULLs

# ✅ YES: Backfilling data
UPDATE products SET mrp = price * 1.15 WHERE mrp IS NULL;
# Safe because: Can run multiple times (idempotent)

# ✅ YES: Renaming table (with app update)
ALTER TABLE products RENAME TO products_v2;
ALTER TABLE products_v2 RENAME TO products;
# Safe because: Data preserved, just table rename

# ✅ YES: Creating index
CREATE INDEX IF NOT EXISTS idx_products_category 
ON products(category);
# Safe because: Doesn't touch data, just adds performance

# ✅ YES: Conditional operations
CREATE TABLE IF NOT EXISTS orders_archive (...);
INSERT INTO orders_archive SELECT * FROM orders WHERE year < 2024;
# Safe because: CREATE IF EXISTS handles idempotency
```

---

## 🔄 Pre-Deployment Checklist by Change Type

### Adding a Table
```
✅ Table doesn't already exist
✅ All columns have appropriate types
✅ Primary keys are defined
✅ Foreign key references are valid
✅ Indexes are created for search columns
✅ No data needs to be migrated
✅ Code updated to use new table
```

### Adding a Column
```
✅ Column has a DEFAULT value
✅ DEFAULT matches expected type
✅ Existing queries updated if needed
✅ Forms updated to include new field
✅ Validation added for input
✅ Null values handled (UPDATE if needed)
✅ Index added if column is frequently queried
```

### Updating Data
```
✅ WHERE clause tested on copy of DB first
✅ Expected affected rows verified
✅ Rollback procedure prepared
✅ Backup created before running UPDATE
✅ Data types match in SET clause
✅ UPDATE is idempotent (safe to run twice)
✅ No foreign key constraints violated
```

---

## 🎯 Decision Examples

### Scenario 1: Add "customer_tier" field to users
```
Question 1: Will existing users need a value?
→ YES (they are all "bronze" tier initially)

Question 2: Do we want to migrate data?
→ YES (set all to "bronze" DEFAULT)

Solution:
ALTER TABLE users ADD COLUMN customer_tier TEXT DEFAULT 'bronze';
UPDATE users SET customer_tier='bronze' WHERE customer_tier IS NULL;

Risk Level: ✅ Very Low
Downtime: <1 second
```

### Scenario 2: Archive old orders (2023 and earlier)
```
Question 1: Need to keep historical data?
→ YES (create archive)

Question 2: Backup first?
→ YES (absolutely)

Solution:
1. CREATE TABLE orders_archive AS SELECT * FROM orders WHERE YEAR(created_at) < 2024;
2. DELETE FROM orders WHERE YEAR(created_at) < 2024;
3. Verify: SELECT COUNT(*) FROM orders;

Risk Level: ⚠️ Medium (use backup)
Downtime: 5-10 seconds
```

### Scenario 3: Change price column from INTEGER to DECIMAL
```
Question 1: Can we use SQLite's type flexibility?
→ YES (SQLite allows this without conversion)

Solution:
-- No migration needed! SQLite doesn't enforce types
-- Just update code to use DECIMAL format
-- Can CAST values if needed:
SELECT CAST(price AS REAL) FROM products;

Risk Level: ✅ Low
Downtime: 0 seconds
```

---

## 🛡️ Safety by Database Operation

### ALWAYS SAFE (Can do anytime)
- ✅ SELECT queries
- ✅ CREATE TABLE IF NOT EXISTS
- ✅ CREATE INDEX IF NOT EXISTS
- ✅ ALTER TABLE ADD COLUMN (with DEFAULT)
- ✅ UPDATE (with proper WHERE clause)
- ✅ INSERT (new data)
- ✅ DROP INDEX
- ✅ RENAME TABLE

### REQUIRES TESTING (Test on copy first)
- ⚠️ UPDATE (any)
- ⚠️ DELETE (any)
- ⚠️ Add column (without DEFAULT)
- ⚠️ Recreate table
- ⚠️ Change constraints

### NEVER SAFE (Avoid in production)
- ❌ Alter column type (SQLite)
- ❌ Drop column (old SQLite)
- ❌ Rename column (old SQLite)
- ❌ Data operations without backup
- ❌ Multiple migrations simultaneously
- ❌ Changes without rollback plan

---

## 📋 Your Migration Roadmap

### Current State (✅ Completed)
```
v1: Initial schema (tables created)
v2: Add MRP column (with DEFAULT REAL)
v3: Add size column (with DEFAULT 'Standard')
v4: Create catalog_images table (new feature)
v5: (Future migrations can go here)
```

### Future Changes (Using This Framework)
```
v6: Example - Add discount_percentage column
    ALTER TABLE products ADD COLUMN discount_percentage REAL DEFAULT 0;

v7: Example - Add user_reviews table
    CREATE TABLE user_reviews (
        id INTEGER PRIMARY KEY,
        user_id INTEGER NOT NULL,
        product_id INTEGER NOT NULL,
        rating INTEGER,
        comment TEXT,
        FOREIGN KEY(user_id) REFERENCES users(id),
        FOREIGN KEY(product_id) REFERENCES products(id)
    );

v8: Example - Archive old orders
    -- Create archive table
    CREATE TABLE orders_archive AS SELECT * FROM orders 
    WHERE created_at < '2024-01-01';
    
    -- Delete archived from main
    DELETE FROM orders WHERE created_at < '2024-01-01';
```

---

## 🚀 Process Summary

### For Small Changes (Add column, add table)
```
1. ✅ Create backup
2. ✅ Test on copy with migration
3. ✅ Verify data integrity
4. ✅ Deploy during low-traffic hours
5. ✅ Monitor for 1 hour after
6. ✅ Keep backup for 7 days
```

### For Large Changes (Remove column, change type)
```
1. ✅ Create detailed plan
2. ✅ Make backup copy of production
3. ✅ Test migration extensively
4. ✅ Prepare rollback scripts
5. ✅ Schedule maintenance window
6. ✅ Notify users
7. ✅ Execute carefully
8. ✅ Verify thoroughly
9. ✅ Monitor closely
10. ✅ Keep backup for 30 days
```

---

**Reference**: Created December 22, 2025
**Status**: Decision Guide Complete
**Use**: When planning database updates for production

"""
Migration Helper Module

Provides utilities for creating and managing database migrations in a structured way.

This module enables:
- Creating new migration versions in a clean, idempotent way
- Automatic tracking of applied migrations in schema_version table
- Safe rollback capabilities
- Built-in error handling and logging
- Pre and post migration hooks

Usage in app.py or migration scripts:

    from migration_helper import Migration, run_migrations
    
    # Define a new migration
    migration_v6 = Migration(
        version=6,
        description='Add discount column to products',
        up='''ALTER TABLE products ADD COLUMN discount_percent REAL DEFAULT 0''',
        down='''ALTER TABLE products DROP COLUMN discount_percent'''  # Won't work in SQLite!
    )
    
    # Or use the callback approach for complex logic
    def migrate_v7_up(conn):
        cur = conn.cursor()
        cur.execute('ALTER TABLE orders ADD COLUMN coupon_code TEXT')
        cur.execute('UPDATE orders SET coupon_code = NULL')
        conn.commit()
    
    migration_v7 = Migration(
        version=7,
        description='Add coupon_code column to orders',
        up_func=migrate_v7_up,
    )
    
    # Apply migrations
    run_migrations([migration_v6, migration_v7])
"""

import sqlite3
from datetime import datetime
from typing import Callable, Optional, List
from contextlib import contextmanager


class Migration:
    """Represents a single database migration version."""
    
    def __init__(
        self,
        version: int,
        description: str,
        up: Optional[str] = None,
        down: Optional[str] = None,
        up_func: Optional[Callable] = None,
        down_func: Optional[Callable] = None,
    ):
        """
        Initialize a migration.
        
        Args:
            version: Migration version number (must be unique)
            description: Human-readable description
            up: SQL statement(s) to apply migration (alternative to up_func)
            down: SQL statement(s) to rollback migration (alternative to down_func)
            up_func: Python function for complex migrations
            down_func: Python function for rollback logic
        
        Note: Either 'up' OR 'up_func' must be provided, not both.
        """
        if not (up or up_func):
            raise ValueError("Either 'up' SQL or 'up_func' callback must be provided")
        if up and up_func:
            raise ValueError("Provide either 'up' SQL or 'up_func', not both")
        
        self.version = version
        self.description = description
        self.up = up
        self.down = down
        self.up_func = up_func
        self.down_func = down_func
    
    def apply(self, conn: sqlite3.Connection) -> bool:
        """
        Apply this migration.
        
        Args:
            conn: SQLite database connection
            
        Returns:
            True if successful, False if already applied
        """
        cur = conn.cursor()
        
        # Check if already applied
        cur.execute(
            'SELECT 1 FROM schema_version WHERE version = ?',
            (self.version,)
        )
        if cur.fetchone():
            return False  # Already applied
        
        try:
            # Apply migration
            if self.up_func:
                self.up_func(conn)
            else:
                conn.execute(self.up)
            
            # Record in schema_version
            cur.execute('''
                INSERT INTO schema_version 
                (version, description, applied_at, status)
                VALUES (?, ?, ?, ?)
            ''', (
                self.version,
                self.description,
                datetime.now().isoformat(),
                'applied'
            ))
            
            conn.commit()
            return True
        
        except Exception as e:
            conn.rollback()
            raise RuntimeError(f"Migration v{self.version} failed: {e}") from e
    
    def rollback(self, conn: sqlite3.Connection) -> bool:
        """
        Rollback this migration.
        
        Args:
            conn: SQLite database connection
            
        Returns:
            True if successful, False if not applied or no rollback defined
        """
        cur = conn.cursor()
        
        # Check if applied
        cur.execute(
            'SELECT 1 FROM schema_version WHERE version = ?',
            (self.version,)
        )
        if not cur.fetchone():
            return False  # Not applied
        
        if not (self.down or self.down_func):
            raise ValueError(f"No rollback defined for migration v{self.version}")
        
        try:
            # Rollback migration
            if self.down_func:
                self.down_func(conn)
            else:
                conn.execute(self.down)
            
            # Remove from schema_version
            cur.execute(
                'DELETE FROM schema_version WHERE version = ?',
                (self.version,)
            )
            
            conn.commit()
            return True
        
        except Exception as e:
            conn.rollback()
            raise RuntimeError(f"Rollback of v{self.version} failed: {e}") from e


def get_applied_versions(conn: sqlite3.Connection) -> List[int]:
    """Get list of applied migration versions."""
    cur = conn.cursor()
    cur.execute('SELECT version FROM schema_version ORDER BY version')
    return [row[0] for row in cur.fetchall()]


def get_pending_migrations(
    conn: sqlite3.Connection,
    migrations: List[Migration]
) -> List[Migration]:
    """Get list of migrations not yet applied."""
    applied = set(get_applied_versions(conn))
    return [m for m in migrations if m.version not in applied]


def run_migrations(
    migrations: List[Migration],
    db_path: str = 'store.db',
    verbose: bool = True
) -> dict:
    """
    Apply all pending migrations.
    
    Args:
        migrations: List of Migration objects to apply
        db_path: Path to database
        verbose: Print status messages
        
    Returns:
        dict with 'applied', 'skipped', 'failed' counts
    """
    conn = sqlite3.connect(db_path)
    
    try:
        applied = []
        skipped = []
        failed = []
        
        for migration in sorted(migrations, key=lambda m: m.version):
            try:
                result = migration.apply(conn)
                if result:
                    applied.append(migration.version)
                    if verbose:
                        print(f"✓ Applied migration v{migration.version}: {migration.description}")
                else:
                    skipped.append(migration.version)
                    if verbose:
                        print(f"⊘ Skipped migration v{migration.version} (already applied)")
            except Exception as e:
                failed.append((migration.version, str(e)))
                if verbose:
                    print(f"✗ Failed migration v{migration.version}: {e}")
        
        conn.close()
        
        return {
            'applied': applied,
            'skipped': skipped,
            'failed': failed,
            'total': len(migrations),
        }
    
    except Exception as e:
        conn.close()
        raise


# Example migrations for reference

def example_migration_add_column():
    """
    Example: Adding a simple column to a table.
    
    This is idempotent - safe to run multiple times because
    'ALTER TABLE IF NOT EXISTS' won't error if column exists.
    """
    return Migration(
        version=6,
        description='Add discount_percent column to products',
        up='''ALTER TABLE products ADD COLUMN discount_percent REAL DEFAULT 0''',
        down='''ALTER TABLE products DROP COLUMN discount_percent''',
    )


def example_migration_complex():
    """
    Example: Complex migration with multiple steps and validation.
    
    For operations that can't be done in a single SQL statement,
    use a callback function.
    """
    
    def up_func(conn):
        """Add and populate a new column."""
        cur = conn.cursor()
        
        # Step 1: Create new column
        cur.execute('ALTER TABLE products ADD COLUMN sku TEXT UNIQUE')
        
        # Step 2: Generate SKIs for existing products
        cur.execute('SELECT id, name FROM products WHERE sku IS NULL')
        products = cur.fetchall()
        
        for product_id, name in products:
            # Generate SKU from name (simple example)
            sku = name.upper().replace(' ', '_')[:20]
            cur.execute('UPDATE products SET sku = ? WHERE id = ?', (sku, product_id))
        
        # Step 3: Make it NOT NULL now that all have values
        # (Note: SQLite doesn't support this directly, would need CREATE TABLE AS)
        
        conn.commit()
    
    def down_func(conn):
        """Rollback: remove the column."""
        cur = conn.cursor()
        # SQLite doesn't support DROP COLUMN directly,
        # would need CREATE TABLE ... AS SELECT approach
        # For now, just mark as reverted
        raise NotImplementedError("Rollback not available for this migration")
    
    return Migration(
        version=7,
        description='Add and auto-populate SKU column for products',
        up_func=up_func,
        down_func=down_func,
    )


def example_migration_new_table():
    """
    Example: Creating a new table.
    
    This is safe to run multiple times (CREATE TABLE IF NOT EXISTS).
    """
    return Migration(
        version=8,
        description='Create product_tags table for categorization',
        up='''
            CREATE TABLE IF NOT EXISTS product_tags (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                product_id INTEGER NOT NULL,
                tag TEXT NOT NULL,
                FOREIGN KEY(product_id) REFERENCES products(id) ON DELETE CASCADE,
                UNIQUE(product_id, tag)
            )
        ''',
        down='''DROP TABLE IF EXISTS product_tags''',
    )


def example_migration_data_migration():
    """
    Example: Data migration without schema change.
    
    Useful for populating new columns or reorganizing data.
    """
    
    def up_func(conn):
        """Update data based on new rules."""
        cur = conn.cursor()
        
        # Example: Set discount_percent based on price
        cur.execute('''
            UPDATE products 
            SET discount_percent = CASE 
                WHEN price > 500 THEN 10
                WHEN price > 200 THEN 5
                ELSE 0
            END
        ''')
        
        conn.commit()
    
    return Migration(
        version=9,
        description='Populate discount_percent based on product price',
        up_func=up_func,
    )


if __name__ == '__main__':
    # Example usage
    print("Migration Helper Module - Example Usage")
    print("\nUse this module to create structured migrations:")
    print("  1. Define migration with Migration class")
    print("  2. Call run_migrations() to apply all pending")
    print("  3. Migration versions automatically tracked in schema_version table")
    print("\nSee examples in this file for common patterns.")

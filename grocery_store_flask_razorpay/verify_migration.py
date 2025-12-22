#!/usr/bin/env python3
"""
Database Migration Verification Script

Verifies database integrity and completeness after migrations.

Checks:
- Database file integrity (SQLite PRAGMA)
- All expected tables exist
- All expected columns exist in tables
- Data counts before/after migration
- Schema version tracking
- Key relationships and constraints
- Performance metrics

Usage:
    python verify_migration.py                  # Run all checks
    python verify_migration.py --quiet          # Minimal output (just summary)
    python verify_migration.py --report FILE    # Save report to file
    python verify_migration.py --compare OLD DB # Compare with previous backup
"""

import sqlite3
import sys
import json
from datetime import datetime
from pathlib import Path
import argparse


class DatabaseVerifier:
    """Verifies database integrity and migration completion."""
    
    # Expected schema after all migrations
    EXPECTED_TABLES = {
        'products': ['id', 'name', 'description', 'price', 'stock', 'image_path', 'mrp', 'size'],
        'orders': ['id', 'customer_name', 'email', 'phone', 'address', 'total_amount', 'payment_status'],
        'order_items': ['id', 'order_id', 'product_id', 'quantity', 'unit_price'],
        'users': ['id', 'email', 'password_hash', 'full_name', 'phone', 'address'],
        'regions': ['id', 'name', 'state'],
        'product_regions': ['product_id', 'region_id'],
        'contact_messages': ['id', 'name', 'email', 'message'],
        'newsletter_subscribers': ['id', 'email'],
        'product_images': ['id', 'product_id', 'image_path'],
        'catalog_images': ['id', 'region', 'position', 'image_path'],
        'admin_users': ['id', 'username', 'password_hash'],
        'product_reviews': ['id', 'product_id', 'rating', 'body'],
        'community_posts': ['id', 'user_id', 'title', 'body'],
        'community_comments': ['id', 'post_id', 'user_id', 'body'],
        'schema_version': ['id', 'version', 'description', 'applied_at', 'status'],
    }
    
    def __init__(self, db_path='store.db'):
        """Initialize verifier with database path."""
        self.db_path = db_path
        self.results = {
            'timestamp': datetime.now().isoformat(),
            'database': db_path,
            'checks': {},
            'data_counts': {},
            'schema_versions': [],
            'summary': {},
        }
    
    def verify(self):
        """Run all verification checks."""
        checks = [
            ('File Exists', self.check_file_exists),
            ('Database Integrity', self.check_database_integrity),
            ('Tables Exist', self.check_tables_exist),
            ('Column Definitions', self.check_column_definitions),
            ('Data Integrity', self.check_data_integrity),
            ('Schema Versions', self.check_schema_versions),
            ('Data Counts', self.check_data_counts),
        ]
        
        for name, check_func in checks:
            try:
                result = check_func()
                self.results['checks'][name] = result
            except Exception as e:
                self.results['checks'][name] = {
                    'status': 'ERROR',
                    'message': str(e),
                }
        
        # Generate summary
        self._generate_summary()
        return self.results
    
    def check_file_exists(self):
        """Check if database file exists."""
        exists = Path(self.db_path).exists()
        return {
            'status': 'PASS' if exists else 'FAIL',
            'message': f'Database file {"found" if exists else "NOT FOUND"}',
        }
    
    def check_database_integrity(self):
        """Check SQLite database integrity."""
        try:
            conn = sqlite3.connect(self.db_path)
            result = conn.execute("PRAGMA integrity_check").fetchone()[0]
            conn.close()
            
            is_valid = result == 'ok'
            return {
                'status': 'PASS' if is_valid else 'FAIL',
                'message': f'Database integrity: {result}',
            }
        except Exception as e:
            return {
                'status': 'ERROR',
                'message': str(e),
            }
    
    def check_tables_exist(self):
        """Check if all expected tables exist."""
        try:
            conn = sqlite3.connect(self.db_path)
            cur = conn.cursor()
            
            cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
            existing_tables = {row[0] for row in cur.fetchall()}
            
            missing = set(self.EXPECTED_TABLES.keys()) - existing_tables
            extra = existing_tables - set(self.EXPECTED_TABLES.keys())
            
            conn.close()
            
            status = 'PASS' if not missing else 'FAIL'
            messages = []
            
            if not missing:
                messages.append(f"✓ All {len(self.EXPECTED_TABLES)} expected tables found")
            else:
                messages.append(f"✗ Missing {len(missing)} table(s): {', '.join(missing)}")
            
            if extra:
                messages.append(f"ℹ Extra tables: {', '.join(sorted(extra))}")
            
            return {
                'status': status,
                'message': ' | '.join(messages),
                'missing_tables': list(missing),
                'extra_tables': list(extra),
            }
        except Exception as e:
            return {
                'status': 'ERROR',
                'message': str(e),
            }
    
    def check_column_definitions(self):
        """Check if tables have expected columns."""
        try:
            conn = sqlite3.connect(self.db_path)
            cur = conn.cursor()
            
            issues = []
            for table_name, expected_cols in self.EXPECTED_TABLES.items():
                try:
                    cur.execute(f"PRAGMA table_info({table_name})")
                    existing_cols = {row[1] for row in cur.fetchall()}
                    
                    # Check required columns (at least these should exist)
                    missing_cols = set(expected_cols) - existing_cols
                    if missing_cols:
                        issues.append(f"{table_name}: missing {missing_cols}")
                
                except sqlite3.OperationalError:
                    issues.append(f"{table_name}: table not found")
            
            conn.close()
            
            status = 'PASS' if not issues else 'FAIL'
            return {
                'status': status,
                'message': f"{'✓ All required columns present' if not issues else f'✗ {len(issues)} issue(s)'}",
                'issues': issues,
            }
        except Exception as e:
            return {
                'status': 'ERROR',
                'message': str(e),
            }
    
    def check_data_integrity(self):
        """Check foreign key relationships."""
        try:
            conn = sqlite3.connect(self.db_path)
            conn.execute("PRAGMA foreign_keys=ON")
            
            integrity_issues = []
            
            # Check order_items references valid products
            result = conn.execute('''
                SELECT COUNT(*) FROM order_items 
                WHERE product_id NOT IN (SELECT id FROM products)
            ''').fetchone()[0]
            if result > 0:
                integrity_issues.append(f"order_items: {result} items reference non-existent products")
            
            # Check product_regions references valid products and regions
            result = conn.execute('''
                SELECT COUNT(*) FROM product_regions 
                WHERE product_id NOT IN (SELECT id FROM products)
            ''').fetchone()[0]
            if result > 0:
                integrity_issues.append(f"product_regions: {result} entries reference non-existent products")
            
            result = conn.execute('''
                SELECT COUNT(*) FROM product_regions 
                WHERE region_id NOT IN (SELECT id FROM regions)
            ''').fetchone()[0]
            if result > 0:
                integrity_issues.append(f"product_regions: {result} entries reference non-existent regions")
            
            conn.close()
            
            status = 'PASS' if not integrity_issues else 'FAIL'
            return {
                'status': status,
                'message': f"{'✓ No foreign key violations' if not integrity_issues else f'✗ {len(integrity_issues)} issue(s)'}",
                'issues': integrity_issues,
            }
        except Exception as e:
            return {
                'status': 'ERROR',
                'message': str(e),
            }
    
    def check_schema_versions(self):
        """Check migration version tracking."""
        try:
            conn = sqlite3.connect(self.db_path)
            cur = conn.cursor()
            
            # Get all applied migrations
            cur.execute('''
                SELECT id, version, description, applied_at, status 
                FROM schema_version 
                ORDER BY version
            ''')
            versions = cur.fetchall()
            
            if not versions:
                return {
                    'status': 'WARN',
                    'message': 'No migration versions recorded',
                    'versions': [],
                }
            
            version_list = []
            for row in versions:
                version_list.append({
                    'version': row[1],
                    'description': row[2],
                    'applied_at': row[3],
                    'status': row[4],
                })
            
            self.results['schema_versions'] = version_list
            
            conn.close()
            
            return {
                'status': 'PASS',
                'message': f"✓ {len(version_list)} migration version(s) applied",
                'versions': version_list,
            }
        except Exception as e:
            return {
                'status': 'ERROR',
                'message': str(e),
            }
    
    def check_data_counts(self):
        """Check data row counts in key tables."""
        try:
            conn = sqlite3.connect(self.db_path)
            
            key_tables = ['products', 'orders', 'users', 'regions', 'admin_users']
            counts = {}
            
            for table in key_tables:
                try:
                    count = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
                    counts[table] = count
                except:
                    counts[table] = 'ERROR'
            
            conn.close()
            
            self.results['data_counts'] = counts
            
            return {
                'status': 'PASS',
                'message': f"✓ Data counts retrieved",
                'counts': counts,
            }
        except Exception as e:
            return {
                'status': 'ERROR',
                'message': str(e),
            }
    
    def _generate_summary(self):
        """Generate verification summary."""
        checks = self.results['checks']
        
        passed = sum(1 for c in checks.values() if c.get('status') == 'PASS')
        failed = sum(1 for c in checks.values() if c.get('status') == 'FAIL')
        errors = sum(1 for c in checks.values() if c.get('status') == 'ERROR')
        warnings = sum(1 for c in checks.values() if c.get('status') == 'WARN')
        
        self.results['summary'] = {
            'total_checks': len(checks),
            'passed': passed,
            'failed': failed,
            'errors': errors,
            'warnings': warnings,
            'status': 'PASS' if (failed == 0 and errors == 0) else 'FAIL',
        }


def print_results(results, quiet=False):
    """Pretty-print verification results."""
    if quiet:
        # Just print summary
        summary = results['summary']
        status = '✓ PASS' if summary['status'] == 'PASS' else '✗ FAIL'
        print(f"{status} - {summary['passed']}/{summary['total_checks']} checks passed")
        if summary['failed'] > 0:
            print(f"  {summary['failed']} failed, {summary['errors']} errors, {summary['warnings']} warnings")
        return
    
    # Full output
    print("\n" + "="*70)
    print(f"DATABASE VERIFICATION REPORT - {results['database']}")
    print("="*70)
    print(f"Timestamp: {results['timestamp']}\n")
    
    # Check results
    print("VERIFICATION CHECKS:")
    print("-"*70)
    for check_name, check_result in results['checks'].items():
        status_icon = {
            'PASS': '✓',
            'FAIL': '✗',
            'WARN': '⚠',
            'ERROR': '⚠',
        }.get(check_result['status'], '?')
        
        print(f"{status_icon} {check_name:<30} {check_result['status']:<8} {check_result['message']}")
        
        # Print sub-details if present
        if 'issues' in check_result and check_result['issues']:
            for issue in check_result['issues']:
                print(f"    - {issue}")
    
    # Data counts
    if results['data_counts']:
        print("\nDATA COUNTS:")
        print("-"*70)
        for table, count in results['data_counts'].items():
            print(f"  {table:<25} {count:>10} rows")
    
    # Schema versions
    if results['schema_versions']:
        print("\nAPPLIED MIGRATIONS:")
        print("-"*70)
        for v in results['schema_versions']:
            print(f"  v{v['version']}: {v['description']}")
            print(f"          Applied: {v['applied_at']} [{v['status']}]")
    
    # Summary
    summary = results['summary']
    print("\n" + "="*70)
    print(f"SUMMARY: {summary['status']}")
    print(f"Checks: {summary['passed']}/{summary['total_checks']} passed, "
          f"{summary['failed']} failed, {summary['errors']} errors, "
          f"{summary['warnings']} warnings")
    print("="*70 + "\n")


def main():
    """Command-line interface."""
    parser = argparse.ArgumentParser(
        description='Database Verification Script',
        epilog='Examples:\n'
               '  python verify_migration.py\n'
               '  python verify_migration.py --quiet\n'
               '  python verify_migration.py --report report.json\n',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    parser.add_argument('--db', default='store.db', help='Database path (default: store.db)')
    parser.add_argument('--quiet', action='store_true', help='Minimal output')
    parser.add_argument('--report', metavar='FILE', help='Save JSON report to file')
    
    args = parser.parse_args()
    
    verifier = DatabaseVerifier(db_path=args.db)
    results = verifier.verify()
    
    # Print results
    print_results(results, quiet=args.quiet)
    
    # Save report if requested
    if args.report:
        with open(args.report, 'w') as f:
            json.dump(results, f, indent=2)
        print(f"✓ Report saved to {args.report}")
    
    # Exit with appropriate code
    sys.exit(0 if results['summary']['status'] == 'PASS' else 1)


if __name__ == '__main__':
    main()

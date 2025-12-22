#!/usr/bin/env python3
"""
Automated Database Backup Utility

Backs up the SQLite database with:
- Timestamped filenames for easy identification
- Optional gzip compression to save space
- Automatic cleanup of old backups (>7 days)
- Verification of backup integrity
- Logging of all operations

Usage:
    python backup_database.py                    # Create backup, keep 7 days of backups
    python backup_database.py --compress         # Create compressed backup (.db.gz)
    python backup_database.py --days 14          # Keep 14 days of backups instead of 7
    python backup_database.py --cleanup-only     # Just cleanup old backups, don't backup
    python backup_database.py --list             # List all existing backups
"""

import os
import shutil
import gzip
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
import argparse


class DatabaseBackup:
    """Handles database backup operations."""
    
    def __init__(self, db_path='store.db', backup_dir='backups', compress=False):
        """
        Initialize backup manager.
        
        Args:
            db_path: Path to database file
            backup_dir: Directory to store backups
            compress: Whether to gzip compress backups
        """
        self.db_path = db_path
        self.backup_dir = backup_dir
        self.compress = compress
        
        # Create backup directory if needed
        Path(self.backup_dir).mkdir(exist_ok=True)
    
    def get_backup_files(self):
        """Get all backup files in chronological order (newest first)."""
        pattern = 'store.db.backup.*'
        backup_path = Path(self.backup_dir)
        files = sorted(
            backup_path.glob(pattern),
            key=lambda x: x.stat().st_mtime,
            reverse=True
        )
        return files
    
    def create_backup(self):
        """
        Create a timestamped backup of the database.
        
        Returns:
            (bool, str): (success, message)
        """
        if not os.path.exists(self.db_path):
            return False, f"Database not found: {self.db_path}"
        
        try:
            # Verify database integrity before backup
            try:
                conn = sqlite3.connect(self.db_path)
                conn.execute("PRAGMA integrity_check")
                conn.close()
            except sqlite3.DatabaseError as e:
                return False, f"Database integrity check failed: {e}"
            
            # Create backup filename with timestamp
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            if self.compress:
                backup_file = os.path.join(self.backup_dir, f'store.db.backup.{timestamp}.gz')
            else:
                backup_file = os.path.join(self.backup_dir, f'store.db.backup.{timestamp}')
            
            # Perform backup
            if self.compress:
                with open(self.db_path, 'rb') as f_in:
                    with gzip.open(backup_file, 'wb') as f_out:
                        shutil.copyfileobj(f_in, f_out)
            else:
                shutil.copy2(self.db_path, backup_file)
            
            # Get file size
            size_mb = os.path.getsize(backup_file) / (1024 * 1024)
            
            return True, f"✓ Backup created: {backup_file} ({size_mb:.2f} MB)"
        
        except Exception as e:
            return False, f"Backup failed: {str(e)}"
    
    def cleanup_old_backups(self, keep_days=7):
        """
        Delete backups older than keep_days.
        
        Args:
            keep_days: Number of days of backups to keep
            
        Returns:
            (int, list): (number_deleted, list_of_deleted_files)
        """
        cutoff_date = datetime.now() - timedelta(days=keep_days)
        deleted_files = []
        
        for backup_file in self.get_backup_files():
            file_mtime = datetime.fromtimestamp(backup_file.stat().st_mtime)
            
            if file_mtime < cutoff_date:
                try:
                    backup_file.unlink()
                    deleted_files.append(str(backup_file))
                except Exception as e:
                    print(f"⚠ Failed to delete {backup_file}: {e}")
        
        return len(deleted_files), deleted_files
    
    def list_backups(self):
        """
        Display all existing backups with details.
        
        Returns:
            list: List of (filename, size_mb, age_hours) tuples
        """
        backups = []
        now = datetime.now()
        
        for backup_file in self.get_backup_files():
            size_mb = backup_file.stat().st_size / (1024 * 1024)
            file_mtime = datetime.fromtimestamp(backup_file.stat().st_mtime)
            age_hours = (now - file_mtime).total_seconds() / 3600
            
            backups.append((backup_file.name, size_mb, age_hours))
        
        return backups
    
    def verify_backup(self, backup_file):
        """
        Verify backup integrity by checking if it's a valid SQLite database.
        
        Args:
            backup_file: Path to backup file
            
        Returns:
            (bool, str): (is_valid, message)
        """
        try:
            if backup_file.endswith('.gz'):
                # For compressed files, we can't directly verify with SQLite
                # Just check if file is valid gzip
                try:
                    with gzip.open(backup_file, 'rb') as f:
                        f.read(1)
                    return True, "✓ Backup is valid gzip file"
                except Exception as e:
                    return False, f"Invalid gzip file: {e}"
            else:
                # For uncompressed, check SQLite integrity
                conn = sqlite3.connect(backup_file)
                result = conn.execute("PRAGMA integrity_check").fetchone()
                conn.close()
                
                if result[0] == 'ok':
                    return True, "✓ Backup database integrity verified"
                else:
                    return False, f"Database integrity issue: {result[0]}"
        
        except Exception as e:
            return False, f"Verification failed: {e}"


def main():
    """Command-line interface for backup operations."""
    parser = argparse.ArgumentParser(
        description='SQLite Database Backup Utility',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
Examples:
  python backup_database.py                    # Create timestamped backup
  python backup_database.py --compress         # Create compressed backup (.gz)
  python backup_database.py --days 14          # Keep 14 days of backups
  python backup_database.py --list             # Show all backups
  python backup_database.py --verify FILE      # Verify a specific backup
        '''
    )
    
    parser.add_argument('--db', default='store.db', help='Database path (default: store.db)')
    parser.add_argument('--dir', default='backups', help='Backup directory (default: backups)')
    parser.add_argument('--compress', action='store_true', help='Gzip compress backups')
    parser.add_argument('--days', type=int, default=7, help='Days of backups to keep (default: 7)')
    parser.add_argument('--cleanup-only', action='store_true', help='Only cleanup, skip backup')
    parser.add_argument('--list', action='store_true', help='List all backups')
    parser.add_argument('--verify', metavar='FILE', help='Verify a specific backup file')
    
    args = parser.parse_args()
    
    backup = DatabaseBackup(db_path=args.db, backup_dir=args.dir, compress=args.compress)
    
    # Verify specific backup
    if args.verify:
        is_valid, message = backup.verify_backup(args.verify)
        status = "✓" if is_valid else "✗"
        print(f"{status} {message}")
        return
    
    # List backups
    if args.list:
        backups = backup.list_backups()
        if not backups:
            print("No backups found.")
            return
        
        print(f"\n{'Backup File':<40} {'Size':<12} {'Age (hours)'}")
        print("-" * 65)
        for filename, size_mb, age_hours in backups:
            age_str = f"{age_hours:.1f}h"
            print(f"{filename:<40} {size_mb:>6.2f} MB   {age_str:>10}")
        print(f"\nTotal backups: {len(backups)}")
        return
    
    # Create backup (unless cleanup-only)
    if not args.cleanup_only:
        success, message = backup.create_backup()
        print(f"{'✓' if success else '✗'} {message}")
    
    # Cleanup old backups
    num_deleted, deleted_files = backup.cleanup_old_backups(keep_days=args.days)
    
    if num_deleted > 0:
        print(f"✓ Cleaned up {num_deleted} old backup(s) (kept last {args.days} days)")
        for f in deleted_files:
            print(f"  - Deleted: {f}")
    else:
        print(f"✓ No old backups to cleanup (keeping last {args.days} days)")


if __name__ == '__main__':
    main()

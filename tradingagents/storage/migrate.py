#!/usr/bin/env python3
"""
Database migration CLI tool for Neon PostgreSQL.

This script provides command-line interface for running database migrations.
"""

import argparse
import logging
import sys
import os
from typing import Optional
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Add the project root to the path so we can import modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from tradingagents.storage.neon_config import NeonConfig
from tradingagents.storage.migrations import MigrationRunner


def setup_logging(verbose: bool = False):
    """Setup logging configuration."""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )


def migrate_up(config: NeonConfig, target_version: Optional[str] = None, verbose: bool = False):
    """Run migrations up to target version."""
    setup_logging(verbose)
    
    runner = MigrationRunner(config)
    
    print("Starting database migration...")
    if target_version:
        print(f"Target version: {target_version}")
    else:
        print("Target version: latest")
    
    success = runner.migrate_up(target_version)
    
    if success:
        print("✅ Migration completed successfully!")
        return 0
    else:
        print("❌ Migration failed!")
        return 1


def migrate_down(config: NeonConfig, target_version: str, verbose: bool = False):
    """Rollback migrations to target version."""
    setup_logging(verbose)
    
    runner = MigrationRunner(config)
    
    print(f"Starting database rollback to version {target_version}...")
    
    success = runner.migrate_down(target_version)
    
    if success:
        print("✅ Rollback completed successfully!")
        return 0
    else:
        print("❌ Rollback failed!")
        return 1


def show_status(config: NeonConfig, verbose: bool = False):
    """Show migration status."""
    setup_logging(verbose)
    
    runner = MigrationRunner(config)
    
    print("Migration Status:")
    print("-" * 80)
    print(f"{'Version':<10} {'Name':<30} {'Applied':<10} {'Integrity':<10}")
    print("-" * 80)
    
    status_list = runner.get_migration_status()
    
    for status in status_list:
        applied_str = "✅ Yes" if status['applied'] else "❌ No"
        integrity_str = "✅ OK" if status['integrity_ok'] else "❌ FAIL"
        
        print(f"{status['version']:<10} {status['name']:<30} {applied_str:<10} {integrity_str:<10}")
    
    print("-" * 80)
    return 0


def validate_schema(config: NeonConfig, verbose: bool = False):
    """Validate database schema."""
    setup_logging(verbose)
    
    runner = MigrationRunner(config)
    
    print("Validating database schema...")
    
    is_valid, issues = runner.validate_schema()
    
    if is_valid:
        print("✅ Schema validation passed!")
        return 0
    else:
        print("❌ Schema validation failed!")
        print("\nIssues found:")
        for issue in issues:
            print(f"  - {issue}")
        return 1


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Database migration tool for Neon PostgreSQL"
    )
    
    parser.add_argument(
        '-v', '--verbose',
        action='store_true',
        help='Enable verbose logging'
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Migrate up command
    up_parser = subparsers.add_parser('up', help='Run migrations')
    up_parser.add_argument(
        '--target',
        help='Target migration version (default: latest)'
    )
    
    # Migrate down command
    down_parser = subparsers.add_parser('down', help='Rollback migrations')
    down_parser.add_argument(
        'target',
        help='Target migration version to rollback to'
    )
    
    # Status command
    subparsers.add_parser('status', help='Show migration status')
    
    # Validate command
    subparsers.add_parser('validate', help='Validate database schema')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return 1
    
    try:
        # Initialize configuration
        config = NeonConfig()
        
        # Validate configuration
        if not config.validate_connection():
            print("❌ Database connection validation failed!")
            print("Please check your NEON_DATABASE_URL environment variable.")
            return 1
        
        # Execute command
        if args.command == 'up':
            return migrate_up(config, args.target, args.verbose)
        elif args.command == 'down':
            return migrate_down(config, args.target, args.verbose)
        elif args.command == 'status':
            return show_status(config, args.verbose)
        elif args.command == 'validate':
            return validate_schema(config, args.verbose)
        else:
            parser.print_help()
            return 1
            
    except Exception as e:
        print(f"❌ Error: {e}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        return 1


if __name__ == '__main__':
    sys.exit(main())
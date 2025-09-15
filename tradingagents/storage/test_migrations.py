"""
Test script for database migrations.

This script provides basic testing functionality for the migration system.
"""

import logging
import sys
import os
from typing import Tuple

# Add the project root to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from tradingagents.storage.neon_config import NeonConfig
from tradingagents.storage.migrations import MigrationRunner


def test_migration_system() -> Tuple[bool, str]:
    """
    Test the migration system functionality.
    
    Returns:
        Tuple of (success, message)
    """
    try:
        # Setup logging
        logging.basicConfig(level=logging.INFO)
        
        # Initialize configuration
        config = NeonConfig()
        
        # Test connection
        if not config.validate_connection():
            return False, "Database connection validation failed"
        
        # Initialize migration runner
        runner = MigrationRunner(config)
        
        # Test migration status (should work even with no migrations applied)
        status = runner.get_migration_status()
        if not isinstance(status, list):
            return False, "Migration status should return a list"
        
        # Test schema validation (may fail if no migrations applied yet)
        is_valid, issues = runner.validate_schema()
        
        # If schema is not valid, try running migrations
        if not is_valid:
            print("Schema validation failed, attempting to run migrations...")
            success = runner.migrate_up()
            if not success:
                return False, "Failed to run migrations"
            
            # Re-validate schema
            is_valid, issues = runner.validate_schema()
            if not is_valid:
                return False, f"Schema still invalid after migration: {issues}"
        
        return True, "Migration system test passed"
        
    except Exception as e:
        return False, f"Migration test failed with exception: {e}"


def main():
    """Main test entry point."""
    print("Testing migration system...")
    
    success, message = test_migration_system()
    
    if success:
        print(f"✅ {message}")
        return 0
    else:
        print(f"❌ {message}")
        return 1


if __name__ == '__main__':
    sys.exit(main())
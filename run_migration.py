#!/usr/bin/env python3
"""
Script to run the database migration to remove final_decision column.
"""

import sys
import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Add the project root to the path
sys.path.append(str(Path(__file__).parent))

from tradingagents.storage.neon_config import NeonConfig
from tradingagents.storage.migrations import MigrationRunner

def main():
    """Run the migration to remove final_decision column."""
    try:
        print("🔄 Running database migration to remove final_decision column...")
        
        # Initialize config and migration runner
        config = NeonConfig()
        runner = MigrationRunner(config)
        
        # Run migrations
        applied_count = runner.run_migrations()
        
        if applied_count > 0:
            print(f"✅ Successfully applied {applied_count} migration(s)")
        else:
            print("✅ No new migrations to apply")
            
        print("🎉 Migration completed successfully!")
        
    except Exception as e:
        print(f"❌ Migration failed: {e}")
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
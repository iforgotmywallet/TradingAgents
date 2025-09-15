#!/usr/bin/env python3
"""
TradingAgents Cleanup Script

This script cleans up temporary files, cache directories, and other artifacts
that shouldn't be committed to version control.
"""

import os
import shutil
import sys
from pathlib import Path


def clean_pycache():
    """Remove all __pycache__ directories"""
    print("🧹 Cleaning __pycache__ directories...")
    count = 0
    for root, dirs, files in os.walk("."):
        if "__pycache__" in dirs:
            cache_path = Path(root) / "__pycache__"
            shutil.rmtree(cache_path)
            count += 1
            print(f"   Removed: {cache_path}")
    print(f"✅ Cleaned {count} __pycache__ directories")


def clean_pyc_files():
    """Remove all .pyc files"""
    print("🧹 Cleaning .pyc files...")
    count = 0
    for root, dirs, files in os.walk("."):
        for file in files:
            if file.endswith(('.pyc', '.pyo')):
                file_path = Path(root) / file
                file_path.unlink()
                count += 1
                print(f"   Removed: {file_path}")
    print(f"✅ Cleaned {count} .pyc files")


def clean_pytest_cache():
    """Remove pytest cache directories"""
    print("🧹 Cleaning pytest cache...")
    count = 0
    for root, dirs, files in os.walk("."):
        if ".pytest_cache" in dirs:
            cache_path = Path(root) / ".pytest_cache"
            shutil.rmtree(cache_path)
            count += 1
            print(f"   Removed: {cache_path}")
    print(f"✅ Cleaned {count} pytest cache directories")


def clean_node_modules():
    """Clean node_modules but keep package files"""
    print("🧹 Checking node_modules...")
    node_modules_path = Path("webapp/node_modules")
    if node_modules_path.exists():
        print("   Found node_modules directory (keeping for development)")
        print("   Run 'npm ci' in webapp/ directory to reinstall if needed")
    else:
        print("   No node_modules directory found")


def clean_temp_files():
    """Remove temporary files"""
    print("🧹 Cleaning temporary files...")
    temp_patterns = ["*.tmp", "*.temp", "*~", ".DS_Store"]
    count = 0
    
    for pattern in temp_patterns:
        for file_path in Path(".").rglob(pattern):
            if file_path.is_file():
                file_path.unlink()
                count += 1
                print(f"   Removed: {file_path}")
    
    print(f"✅ Cleaned {count} temporary files")


def main():
    """Main cleanup function"""
    print("🚀 TradingAgents Cleanup Script")
    print("=" * 40)
    
    # Check if we're in the right directory
    if not Path("tradingagents").exists():
        print("❌ Please run this script from the TradingAgents root directory")
        sys.exit(1)
    
    # Run cleanup functions
    clean_pycache()
    clean_pyc_files()
    clean_pytest_cache()
    clean_temp_files()
    clean_node_modules()
    
    print("\n🎉 Cleanup completed!")
    print("\nProject is ready for commit/push.")


if __name__ == "__main__":
    main()
#!/usr/bin/env python3
"""
TradingAgents Project Verification Script

This script verifies that the project is properly set up and ready for deployment.
"""

import os
import sys
from pathlib import Path
import importlib.util


def check_required_files():
    """Check if all required files exist"""
    print("📁 Checking required files...")
    
    required_files = [
        "requirements.txt",
        "pyproject.toml",
        "setup.py",
        "main.py",
        "README.md",
        "LICENSE",
        ".env.example",
        "webapp/app.py",
        "webapp/run.py",
        "webapp/requirements.txt",
        "cli/main.py",
        "tradingagents/default_config.py",
        "tradingagents/graph/trading_graph.py",
    ]
    
    missing_files = []
    for file_path in required_files:
        if not Path(file_path).exists():
            missing_files.append(file_path)
    
    if missing_files:
        print(f"❌ Missing files: {missing_files}")
        return False
    
    print("✅ All required files present")
    return True


def check_imports():
    """Check if core modules can be imported"""
    print("🔍 Checking core imports...")
    
    try:
        from tradingagents.graph.trading_graph import TradingAgentsGraph
        from tradingagents.default_config import DEFAULT_CONFIG
        print("✅ Core TradingAgents modules OK")
    except ImportError as e:
        print(f"❌ Core import error: {e}")
        return False
    
    try:
        import fastapi
        import uvicorn
        print("✅ Web framework imports OK")
    except ImportError as e:
        print(f"❌ Web framework import error: {e}")
        return False
    
    return True


def check_environment():
    """Check environment setup"""
    print("🔧 Checking environment...")
    
    # Check Python version
    if sys.version_info < (3, 10):
        print(f"❌ Python 3.10+ required, found {sys.version_info.major}.{sys.version_info.minor}")
        return False
    
    print(f"✅ Python {sys.version_info.major}.{sys.version_info.minor} OK")
    
    # Check for .env file
    if not Path(".env").exists():
        print("⚠️  .env file not found - you'll need to set up API keys")
        print("   Copy .env.example to .env and add your API keys")
    else:
        print("✅ .env file found")
    
    return True


def check_project_structure():
    """Check project structure"""
    print("🏗️  Checking project structure...")
    
    required_dirs = [
        "tradingagents",
        "tradingagents/agents",
        "tradingagents/graph",
        "tradingagents/dataflows",
        "tradingagents/storage",
        "webapp",
        "webapp/static",
        "webapp/tests",
        "cli",
    ]
    
    missing_dirs = []
    for dir_path in required_dirs:
        if not Path(dir_path).is_dir():
            missing_dirs.append(dir_path)
    
    if missing_dirs:
        print(f"❌ Missing directories: {missing_dirs}")
        return False
    
    print("✅ Project structure OK")
    return True


def check_no_debug_code():
    """Check for debug code that shouldn't be in production"""
    print("🐛 Checking for debug code...")
    
    # This is a simple check - in a real scenario you might want more sophisticated checks
    debug_patterns = []
    
    # Check main.py for debug=True
    main_py = Path("main.py")
    if main_py.exists():
        content = main_py.read_text()
        if "debug=True" in content:
            debug_patterns.append("main.py contains debug=True")
    
    if debug_patterns:
        print(f"⚠️  Found debug patterns: {debug_patterns}")
        print("   Consider removing debug code for production")
    else:
        print("✅ No obvious debug code found")
    
    return True


def main():
    """Main verification function"""
    print("🚀 TradingAgents Project Verification")
    print("=" * 40)
    
    # Check if we're in the right directory
    if not Path("tradingagents").exists():
        print("❌ Please run this script from the TradingAgents root directory")
        sys.exit(1)
    
    # Run all checks
    checks = [
        check_required_files,
        check_project_structure,
        check_environment,
        check_imports,
        check_no_debug_code,
    ]
    
    passed = 0
    for check in checks:
        try:
            if check():
                passed += 1
            print()  # Add blank line between checks
        except Exception as e:
            print(f"❌ Check failed with error: {e}")
            print()
    
    print("=" * 40)
    print(f"📊 Results: {passed}/{len(checks)} checks passed")
    
    if passed == len(checks):
        print("🎉 Project verification successful!")
        print("✅ Project is ready for commit/push")
        return 0
    else:
        print("❌ Some checks failed. Please fix the issues above.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
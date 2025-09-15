#!/usr/bin/env python3
"""
Test script to verify TradingAgents web app setup
"""

import sys
from pathlib import Path

def test_imports():
    """Test if all required modules can be imported"""
    print("🧪 Testing imports...")
    
    try:
        # Test FastAPI imports
        import fastapi
        import uvicorn
        import websockets
        import pydantic
        print("✅ Web framework dependencies OK")
    except ImportError as e:
        print(f"❌ Web framework import error: {e}")
        return False
    
    try:
        # Test TradingAgents imports
        from tradingagents.graph.trading_graph import TradingAgentsGraph
        from tradingagents.default_config import DEFAULT_CONFIG
        from cli.models import AnalystType
        print("✅ TradingAgents imports OK")
    except ImportError as e:
        print(f"❌ TradingAgents import error: {e}")
        print("Make sure you have installed the main project dependencies:")
        print("pip install -r requirements.txt")
        return False
    
    return True

def test_file_structure():
    """Test if all required files exist"""
    print("📁 Testing file structure...")
    
    required_files = [
        "webapp/app.py",
        "webapp/static/index.html",
        "webapp/static/style.css",
        "webapp/static/app.js",
        "webapp/run.py"
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

def test_config():
    """Test configuration"""
    print("⚙️  Testing configuration...")
    
    try:
        from tradingagents.default_config import DEFAULT_CONFIG
        required_keys = ["llm_provider", "deep_think_llm", "quick_think_llm"]
        
        for key in required_keys:
            if key not in DEFAULT_CONFIG:
                print(f"❌ Missing config key: {key}")
                return False
        
        print("✅ Configuration OK")
        return True
    except Exception as e:
        print(f"❌ Configuration error: {e}")
        return False

def main():
    print("🚀 TradingAgents Web App Test Suite")
    print("=" * 40)
    
    tests = [
        test_file_structure,
        test_imports,
        test_config
    ]
    
    passed = 0
    for test in tests:
        if test():
            passed += 1
        print()
    
    print("=" * 40)
    print(f"📊 Results: {passed}/{len(tests)} tests passed")
    
    if passed == len(tests):
        print("🎉 All tests passed! You can now run the web app:")
        print("   python launch_webapp.py")
        return 0
    else:
        print("❌ Some tests failed. Please fix the issues above.")
        return 1

if __name__ == "__main__":
    sys.exit(main())
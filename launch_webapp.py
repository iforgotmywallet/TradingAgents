#!/usr/bin/env python3
"""
Simple launcher for TradingAgents Web App
Usage: python launch_webapp.py
"""

import sys
import subprocess
import os
from pathlib import Path

def main():
    print("🚀 TradingAgents Web App Launcher")
    print("=" * 40)
    
    # Check if we're in the right directory
    if not Path("webapp").exists():
        print("❌ webapp directory not found. Please run from the TradingAgents root directory.")
        return 1
    
    # Check Python version
    if sys.version_info < (3, 8):
        print("❌ Python 3.8+ is required")
        return 1
    
    print("✅ Python version OK")
    
    # Install dependencies
    print("📦 Installing dependencies...")
    try:
        subprocess.run([sys.executable, "-m", "pip", "install", "-r", "webapp/requirements.txt"], 
                      check=True, capture_output=True)
        print("✅ Web app dependencies installed")
    except subprocess.CalledProcessError as e:
        print(f"⚠️  Warning: Could not install web dependencies: {e}")
    
    # Check for .env file
    if not Path(".env").exists():
        print("⚠️  .env file not found. You may need to set up API keys.")
    
    # Start the web app
    print("🌐 Starting web app at http://localhost:8000")
    print("🛑 Press Ctrl+C to stop")
    print("=" * 40)
    
    try:
        os.chdir("webapp")
        subprocess.run([sys.executable, "run.py"])
    except KeyboardInterrupt:
        print("\n👋 Web app stopped")
    except Exception as e:
        print(f"❌ Error starting web app: {e}")
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
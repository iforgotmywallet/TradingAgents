#!/usr/bin/env python3
import subprocess
import sys
import os

print("🚀 Starting TradingAgents Web App")
print("🌐 Access at: http://localhost:8000")
print("🛑 Press Ctrl+C to stop")
print("=" * 40)

try:
    os.chdir("webapp")
    subprocess.run(["venv/bin/python", "run.py"])
except KeyboardInterrupt:
    print("\n👋 Web app stopped")
except Exception as e:
    print(f"❌ Error: {e}")

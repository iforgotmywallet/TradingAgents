#!/usr/bin/env python3
"""
Test script to check if web app endpoints work
"""

import requests
import time
import subprocess
import sys
from pathlib import Path

def test_endpoints():
    """Test the web app endpoints"""
    base_url = "http://localhost:8001"
    
    print("🧪 Testing web app endpoints...")
    
    # Test health endpoint
    try:
        response = requests.get(f"{base_url}/health", timeout=5)
        if response.status_code == 200:
            print("✅ Health endpoint working")
        else:
            print(f"❌ Health endpoint failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Health endpoint error: {e}")
        return False
    
    # Test main page
    try:
        response = requests.get(f"{base_url}/", timeout=5)
        if response.status_code == 200:
            print("✅ Main page working")
        else:
            print(f"❌ Main page failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Main page error: {e}")
        return False
    
    # Test API endpoints
    api_endpoints = [
        "/api/analyst-options",
        "/api/llm-providers", 
        "/api/research-depth-options"
    ]
    
    for endpoint in api_endpoints:
        try:
            response = requests.get(f"{base_url}{endpoint}", timeout=5)
            if response.status_code == 200:
                print(f"✅ {endpoint} working")
            else:
                print(f"❌ {endpoint} failed: {response.status_code}")
                return False
        except Exception as e:
            print(f"❌ {endpoint} error: {e}")
            return False
    
    return True

def main():
    print("🚀 Starting web app for testing...")
    
    # Start the web app in background
    process = None
    try:
        # Change to webapp directory and start server
        process = subprocess.Popen([
            sys.executable, "run.py"
        ], cwd="webapp", stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        
        # Wait a bit for server to start
        print("⏳ Waiting for server to start...")
        time.sleep(5)
        
        # Test endpoints
        if test_endpoints():
            print("🎉 All endpoints working!")
            return 0
        else:
            print("❌ Some endpoints failed")
            return 1
            
    except Exception as e:
        print(f"❌ Error starting server: {e}")
        return 1
    finally:
        if process:
            process.terminate()
            process.wait()
            print("🛑 Server stopped")

if __name__ == "__main__":
    sys.exit(main())
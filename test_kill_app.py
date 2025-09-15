#!/usr/bin/env python3
"""
Test script for kill_app.py functionality
This creates some test processes and then tests the kill script
"""
import subprocess
import time
import sys
import os
from threading import Thread
import socket

def start_test_server(port):
    """Start a simple HTTP server for testing"""
    try:
        import http.server
        import socketserver
        
        class TestHandler(http.server.SimpleHTTPRequestHandler):
            def log_message(self, format, *args):
                pass  # Suppress log messages
        
        with socketserver.TCPServer(("", port), TestHandler) as httpd:
            print(f"Test server started on port {port}")
            httpd.serve_forever()
    except Exception as e:
        print(f"Failed to start test server on port {port}: {e}")

def test_kill_script():
    """Test the kill_app.py script"""
    print("🧪 Testing kill_app.py script")
    print("=" * 40)
    
    # Start test servers in background
    test_ports = [8001, 8000]
    servers = []
    
    print("🚀 Starting test servers...")
    for port in test_ports:
        try:
            # Start server in background process
            server_process = subprocess.Popen([
                sys.executable, "-c", 
                f"""
import http.server
import socketserver
import signal
import sys

def signal_handler(sig, frame):
    sys.exit(0)

signal.signal(signal.SIGTERM, signal_handler)
signal.signal(signal.SIGINT, signal_handler)

class TestHandler(http.server.SimpleHTTPRequestHandler):
    def log_message(self, format, *args):
        pass

try:
    with socketserver.TCPServer(("", {port}), TestHandler) as httpd:
        print(f"Test server on port {port} ready")
        httpd.serve_forever()
except Exception as e:
    print(f"Server error on port {port}: {{e}}")
"""
            ])
            servers.append((port, server_process))
            time.sleep(0.5)  # Give server time to start
            print(f"   ✅ Test server started on port {port} (PID: {server_process.pid})")
        except Exception as e:
            print(f"   ❌ Failed to start server on port {port}: {e}")
    
    # Wait a moment for servers to be fully ready
    time.sleep(2)
    
    # Check that servers are running
    print("\n🔍 Checking test servers are running...")
    for port, process in servers:
        if process.poll() is None:  # Process is still running
            print(f"   ✅ Server on port {port} is running (PID: {process.pid})")
        else:
            print(f"   ❌ Server on port {port} failed to start")
    
    # Now test the kill script
    print("\n🛑 Running kill_app.py...")
    try:
        result = subprocess.run([sys.executable, "kill_app.py"], 
                              capture_output=True, text=True, timeout=30)
        print("Kill script output:")
        print(result.stdout)
        if result.stderr:
            print("Kill script errors:")
            print(result.stderr)
        print(f"Kill script exit code: {result.returncode}")
    except subprocess.TimeoutExpired:
        print("❌ Kill script timed out")
    except Exception as e:
        print(f"❌ Error running kill script: {e}")
    
    # Check if servers were killed
    print("\n🔍 Checking if test servers were killed...")
    time.sleep(1)  # Give time for processes to terminate
    
    for port, process in servers:
        if process.poll() is None:  # Process is still running
            print(f"   ⚠️  Server on port {port} is still running (PID: {process.pid})")
            # Force kill it
            try:
                process.terminate()
                process.wait(timeout=5)
                print(f"   ✅ Manually terminated server on port {port}")
            except:
                process.kill()
                print(f"   ✅ Force killed server on port {port}")
        else:
            print(f"   ✅ Server on port {port} was successfully killed")
    
    print("\n🎉 Test completed!")

if __name__ == "__main__":
    test_kill_script()
#!/usr/bin/env python3
"""
TradingAgents App Killer Script
This script kills all running processes and ports related to the TradingAgents webapp.
Works on macOS, Linux, and Windows using only built-in Python modules.
"""
import subprocess
import sys
import os
import platform
import time
from typing import List, Optional, Tuple

class ProcessKiller:
    def __init__(self):
        self.system = platform.system()
        self.killed_processes = 0
        self.freed_ports = 0
        self.dry_run = False
        self.verbose = False
        self.custom_ports = None
        
    def run_command(self, cmd: str, shell: bool = True) -> Tuple[bool, str]:
        """Run a shell command and return (success, output)."""
        try:
            result = subprocess.run(cmd, shell=shell, capture_output=True, text=True, timeout=10)
            return result.returncode == 0, result.stdout.strip()
        except subprocess.TimeoutExpired:
            return False, "Command timed out"
        except Exception as e:
            return False, str(e)
    
    def find_processes_by_pattern(self, pattern: str) -> List[str]:
        """Find process IDs matching a pattern using ps/tasklist."""
        pids = []
        current_pid = str(os.getpid())
        
        if self.system == "Windows":
            # Windows version using tasklist
            success, output = self.run_command('tasklist /FO CSV')
            if success and output:
                lines = output.split('\n')[1:]  # Skip header
                for line in lines:
                    if pattern.lower() in line.lower() and line.strip():
                        # Skip kill_app.py itself
                        if 'kill_app.py' in line.lower():
                            continue
                        parts = line.split(',')
                        if len(parts) > 1:
                            pid = parts[1].strip('"')
                            if pid.isdigit() and pid != current_pid:
                                pids.append(pid)
        else:
            # Unix-like systems (macOS, Linux)
            success, output = self.run_command(f'ps aux | grep -E "{pattern}" | grep -v grep | grep -v kill_app.py')
            if success and output:
                for line in output.split('\n'):
                    if line.strip():
                        parts = line.split()
                        if len(parts) > 1 and parts[1].isdigit():
                            pid = parts[1]
                            # Don't kill ourselves
                            if pid != current_pid:
                                pids.append(pid)
        
        return pids
    
    def find_process_by_port(self, port: int) -> Optional[str]:
        """Find process ID using a specific port."""
        if self.system == "Windows":
            success, output = self.run_command(f'netstat -ano | findstr :{port}')
            if success and output:
                lines = output.split('\n')
                for line in lines:
                    if f':{port}' in line and ('LISTENING' in line or 'ESTABLISHED' in line):
                        parts = line.split()
                        if parts and parts[-1].isdigit():
                            return parts[-1]  # Last column is PID
        else:
            # Try lsof first (more reliable)
            success, output = self.run_command(f'lsof -ti:{port}')
            if success and output:
                pid = output.split('\n')[0].strip()
                if pid.isdigit():
                    return pid
            
            # Fallback to netstat
            success, output = self.run_command(f'netstat -tulpn 2>/dev/null | grep :{port}')
            if success and output:
                for line in output.split('\n'):
                    if f':{port}' in line:
                        parts = line.split()
                        for part in parts:
                            if '/' in part:
                                pid = part.split('/')[0]
                                if pid.isdigit():
                                    return pid
        
        return None
    
    def kill_process(self, pid: str, description: str = "") -> bool:
        """Kill a process by PID."""
        if not pid or not pid.isdigit():
            return False
        
        if self.dry_run:
            print(f"   🔍 Would kill PID {pid} {description}")
            return True
            
        try:
            if self.system == "Windows":
                success, output = self.run_command(f'taskkill /F /PID {pid}')
            else:
                # Try graceful kill first, then force kill
                success, _ = self.run_command(f'kill {pid}')
                if not success:
                    time.sleep(1)
                    success, _ = self.run_command(f'kill -9 {pid}')
            
            if success:
                print(f"   ✅ Killed PID {pid} {description}")
                self.killed_processes += 1
                return True
            else:
                print(f"   ⚠️  Could not kill PID {pid} {description}")
                return False
        except Exception as e:
            print(f"   ❌ Error killing PID {pid}: {e}")
            return False
    
    def kill_processes_by_pattern(self, pattern: str, description: str):
        """Kill all processes matching a pattern."""
        print(f"🔍 Looking for {description}...")
        pids = self.find_processes_by_pattern(pattern)
        
        if pids:
            print(f"   Found {len(pids)} processes: {pids}")
            for pid in pids:
                self.kill_process(pid, f"({description})")
        else:
            print(f"   ✅ No {description} found")
    
    def kill_processes_on_ports(self, ports: List[int]):
        """Kill processes using specific ports."""
        print(f"\n🔌 Killing processes on ports: {ports}")
        
        for port in ports:
            pid = self.find_process_by_port(port)
            if pid:
                print(f"🔍 Found process {pid} on port {port}")
                if self.kill_process(pid, f"(port {port})"):
                    self.freed_ports += 1
            else:
                print(f"   ✅ Port {port} is free")
    
    def verify_cleanup(self):
        """Verify that processes and ports are cleaned up."""
        print("\n🔍 Final verification...")
        
        # Check for remaining processes
        remaining_patterns = ["uvicorn", "tradingagents", "webapp", "fastapi"]
        remaining_found = False
        
        for pattern in remaining_patterns:
            pids = self.find_processes_by_pattern(pattern)
            if pids:
                print(f"   ⚠️  Warning: {len(pids)} {pattern} processes still running: {pids}")
                remaining_found = True
        
        if not remaining_found:
            print("   ✅ No remaining TradingAgents processes found")
        
        # Check port status
        print("\n📊 Port status check:")
        key_ports = [8001, 8000, 5000, 3000, 8080]
        
        for port in key_ports:
            pid = self.find_process_by_port(port)
            if pid:
                print(f"   ⚠️  Port {port}: In use by PID {pid}")
            else:
                print(f"   ✅ Port {port}: Free")
    
    def run_cleanup(self):
        """Main cleanup process."""
        print("🛑 TradingAgents App Killer")
        print("=" * 50)
        
        # 1. Kill TradingAgents specific processes
        print("\n🎯 Killing TradingAgents specific processes...")
        
        patterns_to_kill = [
            ("uvicorn", "uvicorn webapp servers"),
            ("run\\.py", "Python webapp runners"),
            ("app\\.py", "Python app processes"),
            ("tradingagents", "TradingAgents processes"),
            ("fastapi", "FastAPI processes"),
            ("webapp.*python", "webapp Python processes"),
            ("python.*webapp", "Python webapp processes"),
        ]
        
        for pattern, description in patterns_to_kill:
            self.kill_processes_by_pattern(pattern, description)
        
        # 2. Kill processes on specific ports
        webapp_ports = self.custom_ports or [8001, 8000, 8080, 3000, 5000, 6000, 7000, 9000]
        self.kill_processes_on_ports(webapp_ports)
        
        # 3. Additional cleanup for Unix systems
        if self.system != "Windows":
            print("\n🧹 Additional Unix cleanup...")
            additional_patterns = [
                ("python.*trading", "Python trading processes"),
                ("jupyter.*trading", "Jupyter trading notebooks"),
                ("pytest.*trading", "Trading test processes"),
                ("gunicorn", "Gunicorn processes"),
                ("celery", "Celery worker processes"),
            ]
            
            for pattern, description in additional_patterns:
                self.kill_processes_by_pattern(pattern, description)
        
        # 4. Wait a moment for processes to terminate
        print("\n⏳ Waiting for processes to terminate...")
        time.sleep(2)
        
        # 5. Final verification
        self.verify_cleanup()
        
        # 6. Summary
        print(f"\n🎉 TradingAgents app cleanup completed!")
        print(f"   📊 Processes killed: {self.killed_processes}")
        print(f"   🔌 Ports freed: {self.freed_ports}")
        print(f"   🚀 Ready to start webapp: cd webapp && python run.py")
        print("=" * 50)

def main():
    """Main function."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Kill TradingAgents webapp processes and free ports')
    parser.add_argument('--dry-run', action='store_true', 
                       help='Show what would be killed without actually killing')
    parser.add_argument('--ports', nargs='+', type=int, 
                       help='Specific ports to check (default: 8001 8000 8080 3000 5000 6000 7000 9000)')
    parser.add_argument('--verbose', '-v', action='store_true',
                       help='Show more detailed output')
    
    args = parser.parse_args()
    
    try:
        killer = ProcessKiller()
        
        # Override ports if specified
        if args.ports:
            killer.custom_ports = args.ports
        
        if args.dry_run:
            killer.dry_run = True
            print("🔍 DRY RUN MODE - No processes will be killed")
        
        if args.verbose:
            killer.verbose = True
        
        killer.run_cleanup()
        return 0
    except KeyboardInterrupt:
        print("\n🛑 Interrupted by user")
        return 1
    except Exception as e:
        print(f"\n❌ Error: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())
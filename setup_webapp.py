#!/usr/bin/env python3
"""
Setup script for TradingAgents Web App
Creates virtual environment and installs dependencies
"""

import sys
import subprocess
import os
from pathlib import Path

def run_command(cmd, description):
    """Run a command and handle errors"""
    print(f"🔄 {description}...")
    try:
        result = subprocess.run(cmd, shell=True, check=True, capture_output=True, text=True)
        print(f"✅ {description} completed")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ {description} failed: {e}")
        if e.stdout:
            print(f"stdout: {e.stdout}")
        if e.stderr:
            print(f"stderr: {e.stderr}")
        return False

def main():
    print("🚀 TradingAgents Web App Setup")
    print("=" * 40)
    
    # Check if we're in the right directory
    if not Path("webapp").exists():
        print("❌ webapp directory not found. Please run from the TradingAgents root directory.")
        return 1
    
    # Create virtual environment
    venv_path = Path("venv")
    if not venv_path.exists():
        if not run_command("python3 -m venv venv", "Creating virtual environment"):
            return 1
    else:
        print("✅ Virtual environment already exists")
    
    # Determine activation script path
    if os.name == 'nt':  # Windows
        activate_script = "venv\\Scripts\\activate"
        pip_cmd = "venv\\Scripts\\pip"
        python_cmd = "venv\\Scripts\\python"
    else:  # Unix/Linux/macOS
        activate_script = "venv/bin/activate"
        pip_cmd = "venv/bin/pip"
        python_cmd = "venv/bin/python"
    
    # Install web app dependencies
    if not run_command(f"{pip_cmd} install -r webapp/requirements.txt", "Installing web app dependencies"):
        return 1
    
    # Install main project dependencies
    if Path("requirements.txt").exists():
        if not run_command(f"{pip_cmd} install -r requirements.txt", "Installing main project dependencies"):
            print("⚠️  Warning: Could not install main dependencies. Some features may not work.")
    
    # Create activation script
    if os.name != 'nt':  # Unix/Linux/macOS
        with open("start_webapp_venv.sh", "w") as f:
            f.write(f"""#!/bin/bash
echo "🚀 Starting TradingAgents Web App"
echo "🌐 Access at: http://localhost:8000"
echo "🛑 Press Ctrl+C to stop"
echo "=" * 40

source {activate_script}
cd webapp
python run.py
""")
        os.chmod("start_webapp_venv.sh", 0o755)
        print("✅ Created start_webapp_venv.sh")
    
    # Create Python launcher that uses venv
    with open("launch_webapp_venv.py", "w") as f:
        f.write(f"""#!/usr/bin/env python3
import subprocess
import sys
import os

print("🚀 Starting TradingAgents Web App")
print("🌐 Access at: http://localhost:8000")
print("🛑 Press Ctrl+C to stop")
print("=" * 40)

try:
    os.chdir("webapp")
    subprocess.run(["{python_cmd.replace('webapp/../', '')}", "run.py"])
except KeyboardInterrupt:
    print("\\n👋 Web app stopped")
except Exception as e:
    print(f"❌ Error: {{e}}")
""")
    
    print("✅ Created launch_webapp_venv.py")
    
    print("\n🎉 Setup complete!")
    print("\nTo start the web app:")
    if os.name != 'nt':
        print("  ./start_webapp_venv.sh")
        print("  OR")
    print(f"  python3 launch_webapp_venv.py")
    print(f"  OR manually: source {activate_script} && cd webapp && python run.py")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
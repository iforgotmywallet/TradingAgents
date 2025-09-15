# TradingAgents App Killer Script

A comprehensive Python script to kill all running processes and free up ports related to the TradingAgents webapp.

## Features

✅ **Cross-platform** - Works on Windows, macOS, and Linux  
✅ **No dependencies** - Uses only built-in Python modules  
✅ **Safe execution** - Won't kill itself or system processes  
✅ **Comprehensive cleanup** - Kills processes by pattern and port  
✅ **Detailed reporting** - Shows exactly what was killed  
✅ **Dry-run mode** - Preview what would be killed without doing it  
✅ **Flexible port targeting** - Specify custom ports to check  

## Quick Usage

```bash
# Basic usage - kill all TradingAgents processes and free ports
python kill_app.py

# Preview what would be killed (safe mode)
python kill_app.py --dry-run

# Target specific ports only
python kill_app.py --ports 8001 8000 5000

# Combine dry-run with specific ports
python kill_app.py --dry-run --ports 8001 8000
```

## What Gets Killed

### 🎯 Process Patterns
- **uvicorn** - Webapp server processes
- **run.py** - Python webapp runners  
- **app.py** - Python app processes
- **tradingagents** - TradingAgents processes
- **fastapi** - FastAPI processes
- **webapp** - General webapp processes
- **jupyter** - Jupyter notebooks (trading-related)
- **pytest** - Test processes (trading-related)
- **gunicorn** - Gunicorn web servers
- **celery** - Celery worker processes

### 🔌 Default Ports
- **8001** - Primary webapp port
- **8000** - Alternative webapp port  
- **8080** - Alternative HTTP port
- **3000** - Development server port
- **5000** - Flask/development port
- **6000-9000** - Other development ports

## Command Line Options

```bash
python kill_app.py [OPTIONS]

Options:
  -h, --help                    Show help message
  --dry-run                     Show what would be killed without killing
  --ports PORT [PORT ...]       Specific ports to check
  --verbose, -v                 Show more detailed output
```

## Examples

### Basic Cleanup
```bash
python kill_app.py
```
Output:
```
🛑 TradingAgents App Killer
==================================================
🎯 Killing TradingAgents specific processes...
🔍 Looking for uvicorn webapp servers...
   ✅ Killed PID 12345 (uvicorn webapp servers)
🔌 Killing processes on ports: [8001, 8000, ...]
🔍 Found process 12346 on port 8001
   ✅ Killed PID 12346 (port 8001)
🎉 TradingAgents app cleanup completed!
   📊 Processes killed: 2
   🔌 Ports freed: 1
```

### Dry Run (Safe Preview)
```bash
python kill_app.py --dry-run
```
Output:
```
🔍 DRY RUN MODE - No processes will be killed
🛑 TradingAgents App Killer
==================================================
🔍 Found process 12345 on port 8001
   🔍 Would kill PID 12345 (port 8001)
```

### Target Specific Ports
```bash
python kill_app.py --ports 8001 8000 5000
```

### Check What's Running First
```bash
# Check what processes are running
ps aux | grep -E "(uvicorn|tradingagents|webapp)" | grep -v grep

# Check what's using ports
lsof -i:8001
lsof -i:8000
lsof -i:5000

# Then run the killer
python kill_app.py
```

## Safety Features

### 🛡️ Built-in Protections
- **Self-protection** - Won't kill the kill_app.py script itself
- **Pattern matching** - Only targets specific process patterns
- **Port-specific** - Only checks development/webapp ports
- **Graceful killing** - Tries SIGTERM before SIGKILL (Unix)
- **Error handling** - Continues even if some kills fail

### 🔍 Verification
- Shows exactly what processes were found and killed
- Reports final port status after cleanup
- Counts total processes killed and ports freed
- Warns about any remaining processes

## Troubleshooting

### Permission Errors
```bash
# macOS/Linux: Run with sudo if needed
sudo python kill_app.py

# Windows: Run as Administrator
# Right-click Command Prompt -> "Run as Administrator"
python kill_app.py
```

### Processes Still Running
```bash
# Check what's still running
python kill_app.py --dry-run

# Force kill specific PID manually
kill -9 <PID>          # Unix
taskkill /F /PID <PID>  # Windows

# Nuclear option (kills ALL Python processes - use carefully!)
pkill python           # Unix
taskkill /F /IM python.exe  # Windows
```

### Ports Still in Use
```bash
# Find what's using a port
lsof -i:8001           # Unix
netstat -ano | findstr :8001  # Windows

# Kill specific port process
python kill_app.py --ports 8001
```

## Integration Examples

### Add to package.json
```json
{
  "scripts": {
    "kill": "python kill_app.py",
    "kill-dry": "python kill_app.py --dry-run",
    "restart": "python kill_app.py && cd webapp && python run.py"
  }
}
```

### Add to Makefile
```makefile
kill:
	python kill_app.py

kill-dry:
	python kill_app.py --dry-run

restart: kill
	cd webapp && python run.py

.PHONY: kill kill-dry restart
```

### Shell Aliases
```bash
# Add to ~/.bashrc or ~/.zshrc
alias killapp="python kill_app.py"
alias killapp-dry="python kill_app.py --dry-run"
alias restart-webapp="python kill_app.py && cd webapp && python run.py"
```

## Testing

The script includes a test suite:

```bash
# Run the test suite
python test_kill_app.py
```

This will:
1. Start test HTTP servers on ports 8001 and 8000
2. Run the kill script
3. Verify the servers were killed
4. Clean up any remaining processes

## When to Use

### ✅ Use when:
- Webapp won't start due to "port already in use" errors
- Need to completely restart the application  
- Processes are hanging or not responding
- Switching between different versions
- Development server is stuck

### ❌ Don't use when:
- You just want to restart (use Ctrl+C instead)
- Other important applications might be affected
- You're unsure what processes are running
- In production environments (use proper process management)

## Platform-Specific Notes

### macOS/Linux
- Uses `ps`, `lsof`, `kill` commands
- Tries graceful SIGTERM before SIGKILL
- Supports process group killing

### Windows  
- Uses `tasklist`, `netstat`, `taskkill` commands
- Uses force kill by default (`/F` flag)
- Handles Windows service processes

## After Running

### Next Steps:
1. **Verify cleanup** - Check the script output
2. **Wait a moment** - Give processes time to fully terminate  
3. **Start webapp** - Run `cd webapp && python run.py`
4. **Check logs** - Look for any startup errors

### Expected Result:
```
🎉 TradingAgents app cleanup completed!
   📊 Processes killed: X
   🔌 Ports freed: Y  
   🚀 Ready to start webapp: cd webapp && python run.py
```

---

**⚠️ Important:** This script is designed to be safe for development environments. Always verify what processes are running before using in shared or production systems.
#!/usr/bin/env python3
"""
TradingAgents Web App Runner

This script starts the TradingAgents web application.
Run with: python webapp/run.py
"""

import uvicorn
import sys
from pathlib import Path

# Add the parent directory to the path so we can import tradingagents
sys.path.append(str(Path(__file__).parent.parent))

if __name__ == "__main__":
    print("🚀 Starting TradingAgents Web App...")
    print("📊 Multi-Agents LLM Financial Trading Framework")
    print("🌐 Access the app at: http://localhost:8001")
    print("=" * 50)
    
    uvicorn.run(
        "app:app",
        host="0.0.0.0",
        port=8001,
        reload=True,
        reload_dirs=["."],
        log_level="info"
    )
#!/usr/bin/env python3
"""
TradingAgents Web App Runner

This script starts the TradingAgents web application.
Run with: python webapp/run.py
"""

import uvicorn
import sys
import os
from pathlib import Path

# Add the parent directory to the path so we can import tradingagents
sys.path.append(str(Path(__file__).parent.parent))

if __name__ == "__main__":
    # Use Railway's PORT environment variable, fallback to 8001 for local development
    port = int(os.environ.get("PORT", 8001))
    
    print("🚀 Starting TradingAgents Web App...")
    print("📊 Multi-Agents LLM Financial Trading Framework")
    print(f"🌐 Access the app at: http://localhost:{port}")
    print("=" * 50)
    
    uvicorn.run(
        "app:app",
        host="0.0.0.0",
        port=port,
        reload=True,
        reload_dirs=["."],
        log_level="info"
    )
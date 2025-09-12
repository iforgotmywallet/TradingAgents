#!/bin/bash
echo "🚀 Starting TradingAgents Web App"
echo "🌐 Access at: http://localhost:8000"
echo "🛑 Press Ctrl+C to stop"
echo "=" * 40

source venv/bin/activate
cd webapp
python run.py

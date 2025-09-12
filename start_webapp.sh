#!/bin/bash

# TradingAgents Web App Startup Script

echo "🚀 TradingAgents Web App Startup"
echo "================================"

# Check if Python is available
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 is required but not installed."
    exit 1
fi

# Check if pip is available
if ! command -v pip &> /dev/null && ! command -v pip3 &> /dev/null; then
    echo "❌ pip is required but not installed."
    exit 1
fi

# Install web app dependencies if needed
echo "📦 Checking web app dependencies..."
if [ -f "webapp/requirements.txt" ]; then
    pip install -r webapp/requirements.txt
else
    echo "⚠️  webapp/requirements.txt not found, installing basic dependencies..."
    pip install fastapi uvicorn websockets pydantic
fi

# Install main project dependencies if needed
echo "📦 Checking main project dependencies..."
if [ -f "requirements.txt" ]; then
    pip install -r requirements.txt
else
    echo "⚠️  Main requirements.txt not found"
fi

# Check if .env file exists
if [ ! -f ".env" ]; then
    echo "⚠️  .env file not found. Please create one with your API keys."
    echo "   You can copy .env.example if it exists."
fi

# Start the web app
echo "🌐 Starting TradingAgents Web App..."
echo "📊 Access the app at: http://localhost:8000"
echo "🛑 Press Ctrl+C to stop the server"
echo "================================"

cd webapp && python run.py
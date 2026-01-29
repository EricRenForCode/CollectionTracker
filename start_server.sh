#!/bin/bash

# Voice Assistant Server Startup Script

# Activate virtual environment if it exists
if [ -d "venv" ]; then
    source venv/bin/activate
fi

# Check if .env file exists
if [ ! -f ".env" ]; then
    echo "⚠️  Warning: .env file not found. Creating from .env.example..."
    if [ -f ".env.example" ]; then
        cp .env.example .env
        echo "✅ Created .env file. Please edit it and add your API keys."
        exit 1
    else
        echo "❌ Error: .env.example not found."
        exit 1
    fi
fi

# Default to development mode
MODE=${1:-dev}

if [ "$MODE" == "prod" ]; then
    echo "🚀 Starting server in PRODUCTION mode with multiple workers..."
    uvicorn app.api.server:app --workers 4 --host 0.0.0.0 --port 8000
elif [ "$MODE" == "dev" ]; then
    echo "🔧 Starting server in DEVELOPMENT mode with auto-reload..."
    uvicorn app.api.server:app --reload --host 127.0.0.1 --port 8000
else
    echo "Usage: $0 [dev|prod]"
    echo "  dev  - Development mode with auto-reload (default)"
    echo "  prod - Production mode with 4 workers"
    exit 1
fi

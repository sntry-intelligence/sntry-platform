#!/bin/bash

# Activation script for AI Agent Framework virtual environment

echo "🚀 Activating AI Agent Framework virtual environment..."

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "❌ Virtual environment not found. Please run:"
    echo "   python3 -m venv venv"
    echo "   source venv/bin/activate"
    echo "   pip install -r shared/requirements.txt"
    exit 1
fi

# Activate virtual environment
source venv/bin/activate

# Verify activation
if [ "$VIRTUAL_ENV" != "" ]; then
    echo "✅ Virtual environment activated: $VIRTUAL_ENV"
    echo "🐍 Python version: $(python --version)"
    echo ""
    echo "Available commands:"
    echo "  python test_setup.py          - Test the setup"
    echo "  ./scripts/start-dev.sh        - Start all services"
    echo "  docker-compose up -d postgres redis  - Start infrastructure only"
    echo ""
    echo "Service URLs (when running):"
    echo "  Auth Service: http://localhost:8001"
    echo "  Data Pipeline: http://localhost:8002"
    echo "  Fine-tuning: http://localhost:8003"
    echo "  Guardrails: http://localhost:8004"
    echo "  Prompt Engineering: http://localhost:8005"
    echo "  RL Training: http://localhost:8006"
else
    echo "❌ Failed to activate virtual environment"
    exit 1
fi
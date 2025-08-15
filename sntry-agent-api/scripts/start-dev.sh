#!/bin/bash

# Development startup script for AI Agent Framework

echo "Starting AI Agent Framework in development mode..."

# Start infrastructure services first
echo "Starting infrastructure services (PostgreSQL, Redis)..."
docker-compose up -d postgres redis

# Wait for services to be ready
echo "Waiting for services to be ready..."
sleep 10

# Start all application services
echo "Starting application services..."
docker-compose up --build

echo "All services started successfully!"
echo ""
echo "Service URLs:"
echo "- Auth Service: http://localhost:8001"
echo "- Data Pipeline Service: http://localhost:8002"
echo "- Fine-tuning Service: http://localhost:8003"
echo "- Guardrails Service: http://localhost:8004"
echo "- Prompt Engineering Service: http://localhost:8005"
echo "- RL Training Service: http://localhost:8006"
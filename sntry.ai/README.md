# sntry.app/ai/v1 REST API Development Framework

A cutting-edge framework for developing, deploying, and managing intelligent AI agents and sophisticated multi-agent systems.

## Architecture

This project follows a microservices architecture with the following services:

- **api-gateway**: Central entry point with authentication, rate limiting, and routing
- **agent-management**: Agent lifecycle management and ADK integration
- **workflow-orchestration**: Multi-agent workflow execution via Vertex AI Agent Engine
- **tool-management**: Tool registration and MCP integration
- **vector-database**: RAG capabilities and semantic search
- **mcp-integration**: Model Context Protocol server management
- **shared**: Common utilities, models, and interfaces

## Tech Stack

- **FastAPI**: Modern, fast web framework for building APIs
- **Prisma**: Next-generation ORM for PostgreSQL
- **PostgreSQL**: Primary database for transactional data
- **Redis**: Caching and session management
- **Docker**: Containerization
- **Google Cloud**: ADK, Vertex AI Agent Engine integration

## Getting Started

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Set up the database:
```bash
prisma generate
prisma db push
```

3. Start services with Docker Compose:
```bash
docker-compose up -d
```

## Development

Each service is independently deployable and follows the same structure:
- `main.py`: FastAPI application entry point
- `routers/`: API route definitions
- `services/`: Business logic
- `models/`: Pydantic models
- `dependencies/`: Dependency injection
- `tests/`: Unit and integration tests

## API Documentation

Once running, API documentation is available at:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc
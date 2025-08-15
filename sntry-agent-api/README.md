# AI Agent Framework

A comprehensive platform that integrates advanced LLM training methodologies, sophisticated orchestration capabilities, and scalable deployment infrastructure for building, training, deploying, and managing intelligent AI agents at scale.

## Architecture Overview

The framework follows a microservices architecture with the following core services:

- **Auth Service** (Port 8001): Authentication and authorization
- **Data Pipeline Service** (Port 8002): Data ingestion, cleaning, and processing
- **Fine-tuning Service** (Port 8003): Model fine-tuning and PEFT
- **Guardrails Service** (Port 8004): AI safety and content moderation
- **Prompt Engineering Service** (Port 8005): Prompt optimization and management
- **RL Training Service** (Port 8006): Reinforcement learning training

## Quick Start

### Prerequisites

- Docker and Docker Compose
- Python 3.11+
- PostgreSQL 15+
- Redis 7+

### Development Setup

1. Clone the repository:
```bash
git clone <repository-url>
cd ai-agent-framework
```

2. Start the infrastructure services:
```bash
docker-compose up -d postgres redis
```

3. Install shared dependencies:
```bash
pip install -r shared/requirements.txt
```

4. Start all services:
```bash
docker-compose up --build
```

### Service URLs

- Auth Service: http://localhost:8001
- Data Pipeline Service: http://localhost:8002
- Fine-tuning Service: http://localhost:8003
- Guardrails Service: http://localhost:8004
- Prompt Engineering Service: http://localhost:8005
- RL Training Service: http://localhost:8006

### Health Checks

Each service provides a health check endpoint at `/health`:

```bash
curl http://localhost:8001/health
```

## Project Structure

```
ai-agent-framework/
├── services/                    # Microservices
│   ├── auth-service/           # Authentication service
│   ├── data-pipeline-service/  # Data processing service
│   ├── fine-tuning-service/    # Model fine-tuning service
│   ├── guardrails-service/     # AI safety service
│   ├── prompt-engineering-service/ # Prompt optimization service
│   └── rl-training-service/    # RL training service
├── shared/                     # Shared utilities and interfaces
│   ├── models/                 # Common data models
│   ├── utils/                  # Utility functions
│   ├── interfaces/             # Base service interfaces
│   └── infrastructure/         # Infrastructure scripts
├── docker-compose.yml          # Multi-service orchestration
└── README.md                   # This file
```

## Development

### Adding a New Service

1. Create service directory under `services/`
2. Implement service using `BaseService` class from `shared/interfaces/base_service.py`
3. Add service to `docker-compose.yml`
4. Create Dockerfile and requirements.txt

### Shared Components

All services share common utilities:

- **Database**: SQLAlchemy with PostgreSQL
- **Caching**: Redis client wrapper
- **Logging**: Standardized logging setup
- **Models**: Common Pydantic models
- **Base Service**: FastAPI service template

## Next Steps

This is the foundational infrastructure. The next tasks will implement:

1. Authentication and security features
2. Data management capabilities
3. LLM training infrastructure
4. Agent orchestration layer
5. API gateway and monitoring

See the implementation plan in `.kiro/specs/ai-agent-framework/tasks.md` for detailed next steps.
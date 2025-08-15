# Technology Stack

## Core Technologies

- **Python 3.11+**: Primary programming language
- **FastAPI**: Web framework for REST APIs
- **SQLAlchemy 2.0+**: ORM for database operations
- **PostgreSQL 15+**: Primary database
- **Redis 7+**: Caching and session storage
- **Docker & Docker Compose**: Containerization and orchestration
- **Pydantic**: Data validation and serialization

## Key Libraries

### Web & API
- `fastapi>=0.104.1` - Modern web framework
- `uvicorn[standard]>=0.24.0` - ASGI server
- `python-multipart>=0.0.6` - Form data handling

### Database & Storage
- `sqlalchemy>=2.0.23` - ORM and database toolkit
- `psycopg2-binary>=2.9.7` - PostgreSQL adapter
- `redis>=5.0.1` - Redis client

### Authentication & Security
- `python-jose[cryptography]>=3.3.0` - JWT handling
- `passlib[bcrypt]>=1.7.4` - Password hashing
- `pydantic[email]>=2.8.0` - Email validation

### AI/ML Libraries
- `transformers>=4.36.0` - Hugging Face transformers
- `torch>=2.1.1` - PyTorch for ML models
- `scikit-learn>=1.3.2` - Machine learning utilities
- `nltk>=3.8.1` - Natural language processing

### Testing
- `pytest>=7.4.3` - Testing framework
- `pytest-asyncio>=0.21.1` - Async testing support
- `httpx>=0.25.2` - HTTP client for testing

## Development Commands

### Environment Setup
```bash
# Start infrastructure services
docker-compose up -d postgres redis

# Install shared dependencies
pip install -r shared/requirements.txt

# Start all services
docker-compose up --build
```

### Service Management
```bash
# Start individual service
docker-compose up auth-service

# View logs
docker-compose logs -f auth-service

# Rebuild service
docker-compose up --build auth-service
```

### Database Operations
```bash
# Access PostgreSQL
docker-compose exec postgres psql -U postgres -d auth_db

# View Redis data
docker-compose exec redis redis-cli
```

### Testing
```bash
# Run tests for specific service
cd services/auth-service && python -m pytest

# Run tests with coverage
python -m pytest --cov=app tests/
```

### Health Checks
```bash
# Check service health
curl http://localhost:8001/health
curl http://localhost:8002/health
curl http://localhost:8003/health
curl http://localhost:8004/health
curl http://localhost:8005/health
curl http://localhost:8006/health
```

## Port Allocation

- 8001: Auth Service
- 8002: Data Pipeline Service  
- 8003: Fine-tuning Service
- 8004: Guardrails Service
- 8005: Prompt Engineering Service
- 8006: RL Training Service
- 5432: PostgreSQL
- 6379: Redis
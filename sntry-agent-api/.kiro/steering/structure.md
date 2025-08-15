# Project Structure & Architecture Patterns

## Directory Organization

```
ai-agent-framework/
├── services/                    # Microservices directory
│   ├── auth-service/           # Authentication & authorization
│   ├── data-pipeline-service/  # Data processing & ingestion
│   ├── fine-tuning-service/    # Model fine-tuning
│   ├── guardrails-service/     # AI safety & content moderation
│   ├── prompt-engineering-service/ # Prompt optimization
│   └── rl-training-service/    # Reinforcement learning
├── shared/                     # Shared utilities & interfaces
│   ├── models/                 # Common Pydantic models
│   ├── utils/                  # Utility functions
│   ├── interfaces/             # Base service interfaces
│   └── infrastructure/         # Infrastructure scripts
├── docker-compose.yml          # Multi-service orchestration
└── README.md                   # Project documentation
```

## Service Structure Pattern

Each service follows this standardized structure:

```
service-name/
├── Dockerfile                  # Container configuration
├── main.py                     # Service entry point
├── requirements.txt            # Service-specific dependencies
├── app/                        # Application code
│   ├── __init__.py
│   ├── models.py              # SQLAlchemy & Pydantic models
│   ├── database.py            # Database configuration
│   ├── routes.py              # FastAPI route handlers
│   └── [service_logic].py     # Core business logic
└── tests/                     # Test suite
    ├── __init__.py
    ├── conftest.py            # Pytest configuration
    └── test_*.py              # Test modules
```

## Architecture Patterns

### Base Service Pattern
- All services inherit from `BaseService` class in `shared/interfaces/base_service.py`
- Provides standardized FastAPI setup, middleware, and exception handling
- Implements common health check endpoint at `/health`

### Database Pattern
- Each service has its own PostgreSQL database
- Uses SQLAlchemy 2.0+ with declarative base models
- Database sessions managed via dependency injection
- Context managers for transaction handling

### Model Pattern
- SQLAlchemy models for database entities
- Pydantic models for API request/response validation
- Shared base models in `shared/models/base.py`
- Consistent naming: `ModelCreate`, `ModelResponse`, `ModelUpdate`

### Route Organization
- Routes organized in separate `routes.py` files
- Use FastAPI routers with tags for API documentation
- Dependency injection for database sessions and authentication

### Error Handling
- Standardized error responses with service identification
- HTTP exception handlers in base service
- Structured error format: `{"error": {"code": "...", "message": "...", "service": "..."}}`

## Coding Conventions

### File Naming
- Snake_case for Python files and directories
- Descriptive names: `test_auth.py`, `data_cleaning.py`
- Service names with hyphens: `auth-service`, `data-pipeline-service`

### Import Organization
- System path manipulation for shared imports: `sys.path.append(os.path.join(os.path.dirname(__file__), '../..'))`
- Shared utilities imported from `shared/` directory
- Service-specific imports from local `app/` directory

### Database Conventions
- Table names in plural: `users`, `roles`, `permissions`
- Foreign key naming: `user_id`, `role_id`
- Association tables for many-to-many: `user_roles`, `role_permissions`
- Timestamps: `created_at`, `updated_at` with timezone support

### API Conventions
- RESTful endpoints with appropriate HTTP methods
- Consistent response formats using Pydantic models
- Health check at `/health` for all services
- API documentation auto-generated via FastAPI

### Testing Patterns
- Pytest with async support (`pytest-asyncio`)
- Test configuration in `conftest.py`
- Test naming: `test_[functionality].py`
- HTTP client testing with `httpx`

## Environment Configuration

### Docker Integration
- Each service has its own Dockerfile
- Multi-service orchestration via docker-compose.yml
- Environment variables for database and Redis connections
- Separate databases per service with shared PostgreSQL instance

### Dependency Management
- Service-specific `requirements.txt` files
- Shared dependencies in `shared/requirements.txt`
- Version pinning for reproducible builds

### Development Setup
- Infrastructure services (PostgreSQL, Redis) started first
- Services can be started individually or together
- Hot reload support via uvicorn in development mode
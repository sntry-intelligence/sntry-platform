# Project Structure

## Architecture Patterns

### Domain-Driven Design
The project follows a domain-driven approach with clear separation of concerns:
- Each business domain has its own module (`business_directory`, `customer_360`)
- Shared infrastructure components in `core/`
- Clear separation between API, business logic, and data layers

### Layered Architecture
```
API Layer (FastAPI routers) → Business Logic → Repository Layer → Database
```

## Directory Structure

### Root Level
- **`app/`**: Main application code
- **`alembic/`**: Database migration scripts
- **`config/`**: Application configuration (logging, etc.)
- **`tests/`**: Test suite organized by domain
- **`logs/`**: Application log files
- **`init-scripts/`**: Database initialization scripts
- **`.kiro/`**: Kiro-specific configuration and specs

### Application Structure (`app/`)

#### Core Infrastructure (`app/core/`)
- **`config.py`**: Centralized configuration using Pydantic Settings
- **`database.py`**: Database connections and session management
- **`celery_app.py`**: Celery configuration and task registration
- **`kafka.py`**: Kafka producer/consumer setup
- **`redis.py`**: Redis connection and caching utilities
- **`tasks.py`**: Shared background tasks

#### Business Domains
Each domain follows the same structure pattern:

**Business Directory (`app/business_directory/`)**
- **`api.py`**: FastAPI router with endpoints
- **`models.py`**: SQLAlchemy database models
- **`schemas.py`**: Pydantic request/response schemas
- **`repository.py`**: Data access layer
- **`tasks.py`**: Domain-specific Celery tasks
- **`scraping/`**: Web scraping components

**Customer 360 (`app/customer_360/`)**
- Same structure as business_directory
- Focused on customer analytics and lead generation

### Database Schemas
- **`business_data`**: Business information and geospatial data
- **`customer_data`**: Customer profiles and interactions
- **`customer_360`**: Data warehouse schema (SQL Server)

## File Naming Conventions

### Python Files
- **`models.py`**: SQLAlchemy database models
- **`schemas.py`**: Pydantic data validation schemas
- **`api.py`**: FastAPI route definitions
- **`repository.py`**: Data access layer
- **`tasks.py`**: Celery background tasks
- **`__init__.py`**: Package initialization (minimal)

### Configuration Files
- **`.env`**: Environment variables (not committed)
- **`.env.example`**: Environment template
- **`pyproject.toml`**: Python project configuration
- **`requirements.txt`**: Python dependencies
- **`alembic.ini`**: Database migration configuration
- **`pytest.ini`**: Test configuration

## Import Conventions

### Absolute Imports
Always use absolute imports from the app root:
```python
from app.core.config import settings
from app.business_directory.models import Business
from app.customer_360.schemas import CustomerResponse
```

### Module Organization
- Keep imports organized: standard library, third-party, local
- Use `from` imports for commonly used items
- Import modules rather than specific functions when many items are needed

## Code Organization Patterns

### API Endpoints
- Group related endpoints in the same router
- Use dependency injection for database sessions
- Implement proper error handling and status codes
- Include comprehensive docstrings for OpenAPI documentation

### Database Models
- Use schema-qualified table names
- Include proper indexes for query performance
- Add created_at/updated_at timestamps
- Use appropriate data types (especially for geospatial data)

### Background Tasks
- Organize tasks by domain in separate `tasks.py` files
- Use appropriate Celery queues for different task types
- Implement proper error handling and retry logic
- Log task execution for monitoring

### Configuration
- Use Pydantic Settings for type-safe configuration
- Group related settings in logical sections
- Provide sensible defaults for development
- Use environment variables for deployment-specific values

## Testing Structure
- Mirror the app structure in tests/
- Use `conftest.py` for shared fixtures
- Separate unit tests from integration tests
- Mock external dependencies (APIs, databases) in unit tests
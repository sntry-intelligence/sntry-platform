# Technology Stack

## Core Framework
- **FastAPI**: Modern Python web framework with automatic OpenAPI documentation
- **Python 3.11+**: Primary programming language with type hints
- **Pydantic**: Data validation and settings management
- **SQLAlchemy 2.0**: ORM with async support

## Databases
- **PostgreSQL with PostGIS**: Primary database for business data with geospatial capabilities
- **Microsoft SQL Server**: Data warehouse for customer analytics (optional)
- **Redis**: Caching and session storage

## Message Queue & Background Processing
- **Apache Kafka**: Event streaming and real-time data processing
- **Celery**: Distributed task queue for background jobs
- **Redis**: Celery broker and result backend

## Web Scraping & Data Processing
- **Playwright**: Browser automation for web scraping
- **BeautifulSoup4**: HTML parsing
- **Pandas/NumPy**: Data manipulation and analysis
- **Google Maps API**: Geocoding and mapping services

## Development & Deployment
- **Docker & Docker Compose**: Containerization
- **Alembic**: Database migrations
- **Uvicorn**: ASGI server

## Code Quality Tools
- **Black**: Code formatting (line length: 100)
- **Flake8**: Linting
- **MyPy**: Type checking
- **Pytest**: Testing framework

## Common Commands

### Development Setup
```bash
# Full development environment setup
make setup

# Start development server
make dev
# or
uvicorn app.main:app --reload

# Install dependencies
make install
```

### Docker Operations
```bash
# Start all services
make docker-up
# or
docker-compose up -d

# Production deployment
make docker-prod-up
# or
docker-compose -f docker-compose.prod.yml up -d

# View logs
make docker-logs
```

### Database Operations
```bash
# Run migrations
make migrate
# or
alembic upgrade head

# Create new migration
make migrate-create
# or
alembic revision --autogenerate -m "Description"
```

### Code Quality
```bash
# Format code
make format
# or
black app/ tests/

# Run linting
make lint
# or
flake8 app/ && mypy app/

# Run tests
make test
# or
pytest

# Run tests with coverage
make test-cov
# or
pytest --cov=app --cov-report=html
```

### Background Tasks
```bash
# Start Celery worker
make celery-worker
# or
celery -A app.core.celery_app worker --loglevel=info

# Start Celery beat scheduler
make celery-beat
# or
celery -A app.core.celery_app beat --loglevel=info

# Monitor with Flower
make celery-flower
# or
celery -A app.core.celery_app flower
```

### Utilities
```bash
# Clean temporary files
make clean

# Database backup
make db-backup

# View application logs
make logs
# or
tail -f logs/app.log
```

## Environment Configuration
- Uses `.env` file for configuration
- Pydantic Settings for type-safe configuration management
- Separate configurations for development/staging/production
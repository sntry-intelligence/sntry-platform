# Jamaica Business Directory - Makefile

.PHONY: help install dev prod test clean lint format docker-build docker-up docker-down migrate

# Default target
help:
	@echo "Available commands:"
	@echo "  install     - Install Python dependencies"
	@echo "  dev         - Start development server"
	@echo "  prod        - Start production server"
	@echo "  test        - Run tests"
	@echo "  test-cov    - Run tests with coverage"
	@echo "  clean       - Clean up temporary files"
	@echo "  lint        - Run linting checks"
	@echo "  format      - Format code with black"
	@echo "  docker-build - Build Docker images"
	@echo "  docker-up   - Start Docker services"
	@echo "  docker-down - Stop Docker services"
	@echo "  migrate     - Run database migrations"
	@echo "  migrate-create - Create new migration"

# Python environment setup
install:
	pip install -r requirements.txt
	playwright install chromium

# Development server
dev:
	uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Production server
prod:
	uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4

# Testing
test:
	pytest

test-cov:
	pytest --cov=app --cov-report=html --cov-report=term

# Code quality
lint:
	flake8 app/
	mypy app/

format:
	black app/
	black tests/

# Docker commands
docker-build:
	docker-compose build

docker-up:
	docker-compose up -d

docker-down:
	docker-compose down

docker-logs:
	docker-compose logs -f

# Production Docker
docker-prod-up:
	docker-compose -f docker-compose.prod.yml up -d

docker-prod-down:
	docker-compose -f docker-compose.prod.yml down

# Database migrations
migrate:
	alembic upgrade head

migrate-create:
	@read -p "Enter migration message: " msg; \
	alembic revision --autogenerate -m "$$msg"

# Celery commands
celery-worker:
	celery -A app.core.celery_app worker --loglevel=info

celery-beat:
	celery -A app.core.celery_app beat --loglevel=info

celery-flower:
	celery -A app.core.celery_app flower

# Cleanup
clean:
	find . -type f -name "*.pyc" -delete
	find . -type d -name "__pycache__" -delete
	find . -type f -name "*.log" -delete
	rm -rf .pytest_cache/
	rm -rf htmlcov/
	rm -rf .coverage
	rm -rf dist/
	rm -rf build/
	rm -rf *.egg-info/

# Database setup
db-init:
	docker-compose exec postgres psql -U postgres -d jamaica_business_db -f /docker-entrypoint-initdb.d/01-init-postgres.sql

# Backup and restore
db-backup:
	docker-compose exec postgres pg_dump -U postgres jamaica_business_db > backup_$(shell date +%Y%m%d_%H%M%S).sql

db-restore:
	@read -p "Enter backup file path: " file; \
	docker-compose exec -T postgres psql -U postgres jamaica_business_db < $$file

# Development utilities
shell:
	python -c "from app.main import app; import IPython; IPython.embed()"

logs:
	tail -f logs/app.log

# Install pre-commit hooks
pre-commit:
	pip install pre-commit
	pre-commit install

# Run all quality checks
check: lint test

# Full development setup
setup: install migrate docker-up
	@echo "Development environment is ready!"
	@echo "API: http://localhost:8000"
	@echo "Docs: http://localhost:8000/docs"
	@echo "Kafka UI: http://localhost:8080"
	@echo "Redis Commander: http://localhost:8081"
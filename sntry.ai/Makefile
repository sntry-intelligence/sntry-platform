# sntry.ai Development Makefile

.PHONY: help install setup-db start stop clean test lint format

help: ## Show this help message
	@echo 'Usage: make [target]'
	@echo ''
	@echo 'Targets:'
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z_-]+:.*?## / {printf "  %-15s %s\n", $$1, $$2}' $(MAKEFILE_LIST)

install: ## Install Python dependencies
	pip install -r requirements.txt

setup-db: ## Set up database and run migrations
	prisma generate
	prisma db push

start: ## Start all services with Docker Compose
	docker-compose up -d

stop: ## Stop all services
	docker-compose down

clean: ## Clean up containers and volumes
	docker-compose down -v
	docker system prune -f

test: ## Run tests
	pytest

lint: ## Run linting
	flake8 .
	mypy .

format: ## Format code
	black .
	isort .

dev-setup: ## Set up development environment
	cp .env.example .env
	make install
	make setup-db

logs: ## View logs from all services
	docker-compose logs -f

logs-api: ## View API Gateway logs
	docker-compose logs -f api-gateway

logs-agent: ## View Agent Management logs
	docker-compose logs -f agent-management

build: ## Build all Docker images
	docker-compose build

rebuild: ## Rebuild and restart all services
	docker-compose down
	docker-compose build
	docker-compose up -d
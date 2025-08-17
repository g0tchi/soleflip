# SoleFlipper Development Makefile

.PHONY: help install install-dev test test-unit test-integration test-api test-cov clean lint format type-check check db-setup db-migrate db-upgrade db-downgrade run dev docker-build docker-up docker-down docs serve-docs

# Default target
help: ## Show this help message
	@echo 'Usage: make [target]'
	@echo ''
	@echo 'Targets:'
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z_-]+:.*?## / {printf "  %-20s %s\n", $$1, $$2}' $(MAKEFILE_LIST)

# Installation
install: ## Install production dependencies
	pip install -e .

install-dev: ## Install development dependencies
	pip install -e ".[dev]"
	pre-commit install

# Testing
test: ## Run all tests
	pytest

test-unit: ## Run unit tests only
	pytest -m unit

test-integration: ## Run integration tests only
	pytest -m integration

test-api: ## Run API tests only
	pytest -m api

test-cov: ## Run tests with coverage report
	pytest --cov=domains --cov=shared --cov-report=html --cov-report=term-missing

test-watch: ## Run tests in watch mode
	pytest --watch

# Code Quality
lint: ## Run linting checks
	ruff check .
	black --check .
	isort --check-only .

format: ## Format code
	black .
	isort .
	ruff --fix .

type-check: ## Run type checking
	mypy domains/ shared/

check: lint type-check test ## Run all quality checks

# Database
db-setup: ## Set up database and run initial migrations
	createdb soleflip || true
	alembic upgrade head

db-migrate: ## Create new migration
	@read -p "Migration name: " name; \
	alembic revision --autogenerate -m "$$name"

db-upgrade: ## Apply all pending migrations
	alembic upgrade head

db-downgrade: ## Rollback one migration
	alembic downgrade -1

db-reset: ## Reset database (WARNING: destroys all data)
	@echo "WARNING: This will destroy all data in the database!"
	@read -p "Are you sure? (y/N): " confirm; \
	if [ "$$confirm" = "y" ] || [ "$$confirm" = "Y" ]; then \
		dropdb soleflip || true; \
		createdb soleflip; \
		alembic upgrade head; \
		echo "Database reset complete."; \
	else \
		echo "Database reset cancelled."; \
	fi

# Development Server
run: ## Run production server
	uvicorn main:app --host 127.0.0.1 --port 8000

dev: ## Run development server with hot reload
	uvicorn main:app --reload --host 127.0.0.1 --port 8000 --log-level debug

dev-watch: ## Run development server with file watching
	watchmedo auto-restart --directory=./domains --directory=./shared --directory=./ --pattern=*.py --recursive -- uvicorn main:app --reload

# Docker
docker-build: ## Build Docker image
	docker build -t soleflip:latest .

docker-up: ## Start services with Docker Compose
	docker-compose up -d

docker-down: ## Stop Docker Compose services
	docker-compose down

docker-logs: ## View Docker Compose logs
	docker-compose logs -f

# Documentation
docs: ## Generate API documentation
	python config/api/api_documentation.py

serve-docs: ## Serve documentation locally
	@echo "API Documentation available at:"
	@echo "  Interactive: http://localhost:8000/docs"
	@echo "  ReDoc: http://localhost:8000/redoc"
	@echo ""
	@echo "Starting development server..."
	make dev

# Data Import
import-sample: ## Import sample data for testing
	@echo "Importing sample data..."
	curl -X POST "http://localhost:8000/api/v1/integration/webhooks/stockx/upload" \
		-F "file=@tests/data/sample_stockx.csv" \
		-F "validate_only=false" || echo "Server not running or sample file missing"

validate-sample: ## Validate sample data without importing
	@echo "Validating sample data..."
	curl -X POST "http://localhost:8000/api/v1/integration/webhooks/stockx/upload" \
		-F "file=@tests/data/sample_stockx.csv" \
		-F "validate_only=true" || echo "Server not running or sample file missing"

# Utilities
clean: ## Clean up temporary files
	find . -type f -name "*.pyc" -delete
	find . -type d -name "__pycache__" -delete
	find . -type d -name "*.egg-info" -exec rm -rf {} +
	rm -rf build/
	rm -rf dist/
	rm -rf htmlcov/
	rm -rf .coverage
	rm -rf .pytest_cache/
	rm -rf .mypy_cache/
	rm -rf .ruff_cache/

health: ## Check application health
	@echo "Checking application health..."
	@curl -s http://localhost:8000/health | python -m json.tool || echo "Application not running or not healthy"

status: ## Show import status
	@echo "Checking import status..."
	@curl -s http://localhost:8000/api/v1/integration/webhooks/import-status | python -m json.tool || echo "Application not running"

# Security
security-check: ## Run security checks
	pip-audit
	bandit -r domains/ shared/

# Performance
benchmark: ## Run performance benchmarks
	pytest tests/ -m "not slow" --benchmark-only

profile: ## Profile the application
	python -m cProfile -o profile_output.prof main.py

# Release
build: ## Build distribution packages
	python -m build

publish-test: ## Publish to test PyPI
	python -m twine upload --repository testpypi dist/*

publish: ## Publish to PyPI
	python -m twine upload dist/*

# Environment
env-check: ## Check environment setup
	@echo "Python version:"
	@python --version
	@echo ""
	@echo "PostgreSQL status:"
	@pg_isready || echo "PostgreSQL not available"
	@echo ""
	@echo "Database exists:"
	@psql -l | grep soleflip || echo "Database 'soleflip' not found"
	@echo ""
	@echo "Required environment variables:"
	@echo "  DATABASE_URL: $${DATABASE_URL:-Not set}"
	@echo "  ENVIRONMENT: $${ENVIRONMENT:-Not set}"

# Backup and Restore
backup: ## Create database backup
	@timestamp=$$(date +%Y%m%d_%H%M%S); \
	pg_dump soleflip > "backup_soleflip_$$timestamp.sql"; \
	echo "Backup created: backup_soleflip_$$timestamp.sql"

restore: ## Restore database from backup (specify BACKUP_FILE=filename)
	@if [ -z "$(BACKUP_FILE)" ]; then \
		echo "Usage: make restore BACKUP_FILE=backup_filename.sql"; \
		exit 1; \
	fi
	@echo "WARNING: This will replace all data in the database!"
	@read -p "Are you sure? (y/N): " confirm; \
	if [ "$$confirm" = "y" ] || [ "$$confirm" = "Y" ]; then \
		dropdb soleflip || true; \
		createdb soleflip; \
		psql soleflip < $(BACKUP_FILE); \
		echo "Database restored from $(BACKUP_FILE)"; \
	else \
		echo "Restore cancelled."; \
	fi

# Monitoring
logs: ## Show application logs
	tail -f logs/application.log

monitor: ## Monitor system resources
	@echo "Monitoring system resources (Ctrl+C to stop)..."
	@while true; do \
		echo "=== $$(date) ==="; \
		echo "CPU and Memory:"; \
		ps aux | grep -E "(python|uvicorn)" | grep -v grep; \
		echo ""; \
		echo "Database connections:"; \
		psql soleflip -c "SELECT count(*) as active_connections FROM pg_stat_activity WHERE state = 'active';" 2>/dev/null || echo "Database not available"; \
		echo ""; \
		sleep 5; \
	done

# Development workflow shortcuts
quick-start: install-dev db-setup ## Quick development setup
	@echo "✅ Development environment ready!"
	@echo "Run 'make dev' to start the development server"

full-check: clean install-dev check test ## Full development check
	@echo "✅ All checks passed!"

deploy-check: clean install test security-check ## Pre-deployment checks
	@echo "✅ Ready for deployment!"
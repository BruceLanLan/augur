.PHONY: install dev test run api clean docker-build docker-up docker-down docker-full lint format

# Install package in editable mode
install:
	pip install -e .

# Install with all dev and optional dependencies
dev:
	pip install -e ".[dev,all]"

# Run test suite
test:
	pytest tests/ -v

# Start dashboard web UI on port 8000
run:
	python -m dashboard.app --port 8000 --cors

# Start REST API server on port 8900
api:
	augur api --port 8900

# Build Docker images
docker-build:
	docker compose build

# Start dashboard container in background
docker-up:
	docker compose up -d dashboard

# Stop all containers
docker-down:
	docker compose down

# Start full stack with all profiles
docker-full:
	docker compose --profile full --profile telegram --profile cron up -d

# Remove Python cache and build artifacts
clean:
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type d -name '.pytest_cache' -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name '.mypy_cache' -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name '.ruff_cache' -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name '*.egg-info' -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name '.eggs' -exec rm -rf {} + 2>/dev/null || true
	rm -rf build/ dist/ .coverage htmlcov/ 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete

# Run linters (no-op placeholder; install ruff/mypy as needed)
lint:
	@echo "No linters configured. Install ruff/mypy and add commands here."

# Run formatter (no-op placeholder; install black/ruff as needed)
format:
	@echo "No formatter configured. Install black/ruff and add commands here."

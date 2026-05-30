.PHONY: install dev test run docker-build docker-up docker-down

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

# Remove Python cache files
clean:
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete

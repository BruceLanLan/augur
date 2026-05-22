.PHONY: install dev test run docker-build docker-up docker-down

install:
	pip install -e .

dev:
	pip install -e ".[dev,all]"

test:
	pytest tests/ -v

run:
	python -m dashboard.app --port 8000 --cors

api:
	augur api --port 8900

docker-build:
	docker compose build

docker-up:
	docker compose up -d dashboard

docker-down:
	docker compose down

docker-full:
	docker compose --profile full --profile telegram --profile cron up -d

clean:
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete

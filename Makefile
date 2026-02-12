SHELL := /bin/bash
.PHONY: help install dev test lint format clean migrate upgrade downgrade docker-up docker-down

help:
	@echo "Срочные Услуги - Backend Makefile"
	@echo ""
	@echo "Commands:"
	@echo "  make install      - Install dependencies"
	@echo "  make dev          - Run development server"
	@echo "  make test         - Run tests"
	@echo "  make lint         - Lint code"
	@echo "  make format       - Format code"
	@echo "  make migrate      - Generate migration"
	@echo "  make upgrade      - Apply migrations"
	@echo "  make downgrade    - Rollback migration"
	@echo "  make docker-up    - Start Docker containers"
	@echo "  make docker-down  - Stop Docker containers"
	@echo "  make clean        - Clean cache files"

install:
	./venv/bin/pip install -r requirements.txt

dev:
	./venv/bin/uvicorn app.main:app --reload --port 10001

test:
	./venv/bin/pytest -v --cov=app

lint:
	./venv/bin/ruff check app tests
	./venv/bin/mypy app

format:
	./venv/bin/black app tests
	./venv/bin/ruff check --fix app tests

migrate:
	@read -p "Enter migration message: " msg; \
	./venv/bin/alembic revision --autogenerate -m "$$msg"

upgrade:
	./venv/bin/alembic upgrade head

downgrade:
	./venv/bin/alembic downgrade -1

docker-up:
	docker compose up -d

docker-down:
	docker compose down

clean:
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	find . -type d -name ".pytest_cache" -exec rm -rf {} +
	find . -type d -name ".mypy_cache" -exec rm -rf {} +
	find . -type d -name ".ruff_cache" -exec rm -rf {} +

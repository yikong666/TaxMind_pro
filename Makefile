SHELL := /bin/bash
.DEFAULT_GOAL := help

.PHONY: help bootstrap api worker scheduler web lint typecheck test contracts check

help: ## Show available commands
	@awk 'BEGIN {FS = ":.*## "} /^[a-zA-Z0-9_-]+:.*## / {printf "%-24s %s\n", $$1, $$2}' $(MAKEFILE_LIST)

bootstrap: ## Install backend and frontend dependencies
	cd apps/backend && uv sync --all-groups
	pnpm install --frozen-lockfile=false

api: ## Run FastAPI with reload
	cd apps/backend && uv run uvicorn taxmind.entrypoints.api.main:create_app --factory --reload --port 8000

worker: ## Run Celery worker for asynchronous maintenance tasks
	cd apps/backend && uv run celery -A taxmind.entrypoints.worker.celery_app:app worker -l INFO

scheduler: ## Run Celery Beat scheduler
	cd apps/backend && uv run celery -A taxmind.entrypoints.worker.celery_app:app beat -l INFO

web: ## Run React dev server
	pnpm --filter @taxmind/web dev

lint: ## Run backend and frontend linters
	cd apps/backend && uv run ruff check src tests
	pnpm lint:web

typecheck: ## Run Python and TypeScript type checks
	cd apps/backend && uv run mypy src tests
	pnpm typecheck:web

test: ## Run unit and contract tests
	cd apps/backend && uv run pytest tests
	pnpm test:web

contracts: ## Export OpenAPI and generate web types
	bash scripts/export-openapi.sh
	bash scripts/generate-web-client.sh

check: lint typecheck test ## Run the local merge gate

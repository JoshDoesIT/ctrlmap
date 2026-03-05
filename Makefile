.PHONY: setup test test-unit test-eval test-integration lint format build clean demo

## Setup ──────────────────────────────────────────────────────────────
setup: ## Install all dependencies including Ollama, llama3, and ragas
	@./scripts/setup.sh

## Test ───────────────────────────────────────────────────────────────
test: test-unit test-integration ## Run all non-eval tests

test-unit: ## Run unit tests
	uv run pytest tests/unit/ -v

test-integration: ## Run integration tests
	uv run pytest tests/integration/ -v

test-eval: ## Run evaluation tests (requires Ollama)
	uv run pytest tests/evaluation/ -m eval -v -s

test-all: test test-eval ## Run everything including eval tests

## Code Quality ───────────────────────────────────────────────────────
lint: ## Run linter
	uv run ruff check .

format: ## Format code
	uv run ruff format .

check: lint ## Lint and format check
	uv run ruff format --check .

## Build ──────────────────────────────────────────────────────────────
build: ## Build wheel and sdist
	uv build

install: ## Install via uv tool (isolated env)
	uv tool install --force .

## Demo ───────────────────────────────────────────────────────────────
demo: ## Run the end-to-end demo (requires Ollama + llama3)
	@./scripts/demo.sh

## Clean ──────────────────────────────────────────────────────────────
clean: ## Remove build artifacts and demo output
	rm -rf dist/ build/ *.egg-info .pytest_cache .ruff_cache demo/output/
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true

## Help ───────────────────────────────────────────────────────────────
help: ## Show available targets
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

.DEFAULT_GOAL := help

.PHONY: setup test test-unit test-eval test-eval-fast eval-run model-compare test-integration lint format typecheck build clean demo docs docs-serve

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

test-eval-fast: ## Quick eval: run E2E scenario only (fast iteration)
	uv run pytest tests/evaluation/test_end_to_end_scenario.py -m eval -v -s

eval-run: ## Run all eval suites via the prompt regression harness
	uv run python tests/evaluation/eval_runner.py

model-compare: ## Compare models on eval suites (MODELS="llama3 qwen2.5:14b")
	uv run python tests/evaluation/model_compare.py $(MODELS)

test-all: test test-eval ## Run everything including eval tests

## Code Quality ───────────────────────────────────────────────────────
lint: ## Run linter
	uv run ruff check .

format: ## Format code
	uv run ruff format .

typecheck: ## Run mypy type checking
	uv run mypy src/

check: lint typecheck ## Lint, type-check, and format check
	uv run ruff format --check .

## Build ──────────────────────────────────────────────────────────────
build: ## Build wheel and sdist
	uv build

install: ## Install via uv tool (isolated env)
	uv tool install --force .

## Docs ───────────────────────────────────────────────────────────────
docs: ## Build API documentation
	uv run mkdocs build

docs-serve: ## Serve docs locally with live-reload
	uv run mkdocs serve

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

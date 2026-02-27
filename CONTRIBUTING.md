# Contributing to ctrlmap

Thanks for your interest in contributing to ctrlmap. This guide covers the development setup, coding standards, and contribution workflow.

## Development Setup

1. **Clone the repository**

```bash
git clone https://github.com/JoshDoesIT/ctrlmap.git
cd ctrlmap
```

2. **Run the setup script** (installs Python deps, Ollama, and llama3)

```bash
make setup
```

This single command installs everything needed to develop and test ctrlmap.

3. **Verify the setup**

```bash
make test
```

## Test-Driven Development (TDD)

This project strictly follows the Red-Green-Refactor cycle. Every feature and bug fix must begin with a failing test.

1. **RED**: Write a test that describes the expected behavior. Run it and confirm it fails.
2. **GREEN**: Write the minimal code needed to make the test pass.
3. **REFACTOR**: Clean up the code while keeping all tests green.

No production code is merged without a corresponding test that was written first.

## Coding Standards

- **Linting**: [Ruff](https://docs.astral.sh/ruff/) handles both linting and formatting
- **Type checking**: [mypy](https://mypy.readthedocs.io/) in strict mode
- **Pre-commit hooks**: Configured via `.pre-commit-config.yaml`

Run all checks locally before pushing:

```bash
make lint          # Ruff linter
make format        # Ruff formatter
make test          # Unit + integration tests
make test-eval     # Evaluation tests (requires Ollama)
```

## Commit Conventions

This project uses [Conventional Commits](https://www.conventionalcommits.org/). Every commit message must follow this format:

```
<type>(<scope>): <description>

[optional body]

[optional footer(s)]
```

Common types:

| Type       | Purpose                            |
|------------|------------------------------------|
| `feat`     | New feature                        |
| `fix`      | Bug fix                            |
| `test`     | Adding or updating tests           |
| `docs`     | Documentation changes              |
| `refactor` | Code restructuring (no behavior change) |
| `chore`    | Tooling, CI, dependency updates    |

## Pull Request Process

1. Create a feature branch from `main` (e.g., `feat/your-feature-name`)
2. Make your changes following TDD
3. Ensure all checks pass (`pytest`, `ruff`, `mypy`)
4. Open a PR using the provided template
5. Reference the relevant issue (e.g., `Fixes #XX`)

## Project Structure

```
ctrlmap/
├── src/ctrlmap/         # Application source code
│   ├── cli.py           # Typer command routing
│   ├── parse/           # PDF ingestion and chunking
│   ├── index/           # Embedding and vector storage
│   ├── map/             # Mapping, harmonization, and clustering
│   ├── llm/             # Ollama client and structured outputs
│   ├── export/          # CSV, Markdown, OSCAL formatters
│   └── models/          # Pydantic schemas
├── tests/
│   ├── unit/            # Fast, isolated unit tests
│   ├── integration/     # End-to-end integration tests
│   └── evaluation/      # Non-deterministic eval tests (requires Ollama)
└── pyproject.toml
```

## License

By contributing, you agree that your contributions will be licensed under the MIT License.

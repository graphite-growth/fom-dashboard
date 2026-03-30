# Backend Development Guide

## Build & Test Commands

### Using uv (recommended)

- Install dependencies: `uv sync`
- Update lock file: `uv lock`

### Testing and linting

- Run single test: `uv run pytest -n auto tests/path/to/test_file.py::test_function_name -v`
- Run linter: `uv run ruff check --fix` and `uv run ruff format --check`
- Test typing: `uv run mypy .`
- **Note**: Only run tests the functions that are affected by changes. Run them in a single command to leverage parallelization.
- **Note**: Run linter and test typing as a validation step.

## Technical Stack

- **Python version**: Python 3.13+
- **Project config**: `pyproject.toml` for configuration and dependency management
- **Environment**: Use virtual environment in `.venv` for dependency isolation
- **Package management**: Use `uv` for faster, more reliable dependency management with lock file
- **Dependencies**: Separate production and dev dependencies in `pyproject.toml`
- **Linting**: `ruff` for style and error checking
- **Type checking**: Use mypy

## Code Style Guidelines

- **Formatting**: Black-compatible formatting via `ruff format`
- **Imports**: Sort imports with `ruff` (stdlib, third-party, local)
- **Type hints**: Use native Python type hints (e.g., `list[str]` not `List[str]`)
- **Documentation**: Google-style docstrings for all modules, classes, functions
- **Naming**: snake_case for variables/functions, PascalCase for classes
- **Function length**: Keep functions short (< 30 lines) and single-purpose
- **PEP 8**: Follow PEP 8 style guide (enforced via `ruff`)

## Python Best Practices

- **Debugging**: Use `logging` module instead of `print`
- **Error handling**: Use specific exceptions with context messages and proper logging
- **Data structures**: Use list/dict comprehensions for concise, readable code
- **Function arguments**: Avoid mutable default arguments
- **Data containers**: Leverage `dataclasses` to reduce boilerplate
- **Configuration**: Use environment variables (via `python-dotenv`) for configuration
- **Security**: Never store/log AWS credentials, set command timeouts

## Development Patterns & Best Practices

- **Favor simplicity**: Choose the simplest solution that meets requirements
- **DRY principle**: Avoid code duplication; reuse existing functionality
- **Configuration management**: Use environment variables for different environments
- **Focused changes**: Only implement explicitly requested or fully understood changes
- **Preserve patterns**: Follow existing code patterns when fixing bugs
- **File size**: Keep files under 300 lines; refactor when exceeding this limit
- **Test coverage**: Write comprehensive unit and integration tests with `pytest`; include fixtures. Create new tests everytime new functionality is added.
- **Test structure**: Use table-driven tests with parameterization for similar test cases
- **Test data**: Express all reusable test data as `@pytest.fixture` functions — never as module-level constants or helper functions prefixed with `_`.
- **Public over private**: Only mark helpers private (`_`) if they are internal implementation details. If a helper can be tested or reused independently, make it public.
- **Mocking**: Use unittest.mock for external dependencies; don't test implementation details
- **Modular design**: Create reusable, modular components
- **Logging**: Implement appropriate logging levels (debug, info, error)
- **Error handling**: Implement robust error handling for production reliability
- **Security best practices**: Follow input validation and data protection practices
- **Performance**: Optimize critical code sections when necessary
- **Dependency management**: Add libraries only when essential
  - When adding/updating dependencies, update `pyproject.toml` first
  - Regenerate the lock file
  - Install the new dependencies with `uv sync`

## Development Workflow

- **Impact assessment**: Evaluate how changes affect other codebase areas
- **Documentation**: Keep documentation up-to-date for complex logic and features
- **Dependencies**: When adding dependencies, always update the `uv.lock` file
- **CI/CD**: All changes should pass CI checks (tests, linting, etc.) before merging

# Repository Guidelines

## Project Structure & Module Organization
Python sources live in `src/rename_movies`, exposed through the `rename_movies` package. CLI entry points are wired via `pyproject.toml` (`rename-movies = rename_movies:main`). Add new commands under `src/rename_movies/__init__.py` or split helpers into sibling modules inside `src/rename_movies`. Tests belong in `tests/` mirroring the package layout (e.g., `tests/test_cli.py`). Keep temporary assets under `tmp/` or `.cache/` and never commit media files; sample inputs should go in `fixtures/` with descriptive filenames.

## Build, Test, and Development Commands
- `uv run rename-movies foo <source> --dest <dest>`: invoke the CLI with the dependencies resolved via `uv`.
- `uv run pytest`: run the test suite (also exposed through `make test`).
- `uv run ruff check --fix`: lint and auto-fix formatting issues.
- `uv run mypy src`: type-check the codebase.
Install new deps with `uv add <package>` so `pyproject.toml` and `uv.lock` stay in sync.

## Coding Style & Naming Conventions
Target Python 3.12+, using Ruff’s defaults plus the enforced rules in `pyproject.toml` (no ambiguous variable names). Prefer dataclasses or attrs-like patterns over ad-hoc dicts. Functions and modules should use snake_case; Click command names stay kebab-case. Keep CLI options explicit and documented in help strings. Use type hints everywhere and avoid implicit `Any`. Indent with 4 spaces and limit lines to 100 characters.

## Testing Guidelines
Write pytest tests alongside new features and name files `test_<feature>.py`. Favor parametrized tests for path-heavy logic and use pathlib fixtures rather than raw strings. When adding filesystem behavior, leverage `tmp_path` or `tmp_path_factory`. Aim to keep coverage for CLI parsing and file renaming paths; add regression tests for bugs before fixing them.

## Commit & Pull Request Guidelines
Use short, imperative commit subjects (`Add batch rename command`). Reference issue IDs in the body when applicable. PRs should explain motivation, list major changes, include before/after behavior, and mention any CLI flag additions. Attach screenshots or terminal transcripts when user-facing output changes. Ensure CI commands (`pytest`, `ruff`, `mypy`) pass before requesting review.

.PHONY: ci
ci: lint test

.PHONY: test
test:
	uv run py.test -vv tests

.PHONY: lint
lint: flake8 mypy ruff

.PHONY: flake8
flake8:
	uv run flake8 src
	uv run flake8 tests

.PHONY: mypy
mypy:
	uv run mypy src
	uv run mypy tests

.PHONY: ruff
ruff:
	uv run ruff check src
	uv run ruff check tests

.PHONY: fix
fix:
	uv run ruff check --fix src
	uv run ruff check --fix tests

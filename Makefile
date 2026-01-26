.PHONY: ci
ci: lint test

.PHONY: test
test:
	py.test -vv tests

.PHONY: lint
lint: flake8 mypy ruff

.PHONY: flake8
flake8:
	flake8 src
	flake8 tests

.PHONY: mypy
mypy:
	mypy src
	mypy tests

.PHONY: ruff
ruff:
	ruff check src
	ruff check tests

.PHONY: fix
fix:
	ruff check --fix src
	ruff check --fix tests

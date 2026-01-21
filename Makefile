.PHONY: ci
ci: lint test

.PHONY: test
test:
	py.test tests

.PHONY: lint
lint: flake8 mypy

.PHONY: flake8
flake8:
	flake8 src
	flake8 tests

.PHONY: mypy
mypy:
	mypy src
	mypy tests

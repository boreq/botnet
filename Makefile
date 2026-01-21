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

.PHONY: mypy
mypy:
	mypy src

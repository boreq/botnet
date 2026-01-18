.PHONY: test
test: test_botnet test_examples

.PHONY: test_botnet
test_botnet:
	py.test tests

.PHONY: test_examples
test_examples:
	py.test examples/tests.py

.PHONY: lint
lint: flake8 mypy

.PHONY: flake8
flake8:
	flake8 botnet

.PHONY: mypy
mypy:
	mypy --warn-no-return --ignore-missing-imports botnet

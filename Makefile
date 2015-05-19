test: test_botnet test_examples

test_botnet:
	py.test tests

test_examples:
	py.test examples/tests.py

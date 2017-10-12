SRC_DIR = ./botnet/modules/builtin/mumble/proto
DST_DIR = ./botnet/modules/builtin/mumble

test: test_botnet test_examples

test_botnet:
	py.test tests

test_examples:
	py.test examples/tests.py

pyflakes:
	pyflakes botnet

mypy:
	mypy --warn-no-return --ignore-missing-imports botnet

update_mumble_proto:
	curl https://raw.githubusercontent.com/mumble-voip/mumble/master/src/Mumble.proto > botnet/modules/builtin/mumble/proto/mumble.proto
	protoc -I=$(SRC_DIR) --python_out=$(DST_DIR) $(SRC_DIR)/mumble.proto

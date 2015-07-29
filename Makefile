SRC_DIR = ./botnet/modules/builtin/mumble/proto
DST_DIR = ./botnet/modules/builtin/mumble

protobuf:
	protoc -I=$(SRC_DIR) --python_out=$(DST_DIR) $(SRC_DIR)/mumble.proto

test: test_botnet test_examples

test_botnet:
	py.test tests

test_examples:
	py.test examples/tests.py

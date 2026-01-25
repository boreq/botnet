from botnet.helpers import load_json, save_json


def test_load_save_json(tmp_file):
    data = {'key': 'value'}
    save_json(tmp_file, data)
    loaded_data = load_json(tmp_file)
    assert loaded_data == data

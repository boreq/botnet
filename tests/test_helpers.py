from botnet.helpers import load_json, save_json, is_channel_name


def test_load_save_json(tmp_file):
    data = {'key': 'value'}
    save_json(tmp_file, data)
    loaded_data = load_json(tmp_file)
    assert loaded_data == data


def test_is_channel_name():
    assert is_channel_name('#channel')
    assert not is_channel_name('')
    assert not is_channel_name('nickname_')

from botnet.config import Config


def test_base():
    c = Config()
    assert c == {}


def test_defaults():
    defaults = {'key': 'value'}
    c = Config(defaults)
    assert c['key'] == 'value'


def test_from_json(tmp_file):
    # Write json to tmp file
    val = '{"key": "value", "dkey": "new"}'
    with open(tmp_file, 'w') as f:
        f.write(val)

    # Defaults
    defaults = {'dkey': 'dvalue'}
    c = Config(defaults)
    assert c['dkey'] == 'dvalue'

    # Should override defaults
    c.from_json_file(tmp_file)
    assert c['key'] == 'value'
    assert c['dkey'] == 'new'

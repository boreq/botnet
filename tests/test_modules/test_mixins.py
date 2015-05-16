import pytest
from botnet.config import Config
from botnet.modules import ConfigMixin, BaseIdleModule


def test_config():
    def get_config():
        config = {
            'modules': ['a', 'b'],
            'module_config': {
                'botnet': {
                    'base_responder': {
                        'overwrite': {
                            'c': 'o',
                         },
                        'only_base_config': 'v'
                    }
                },
                'testing': {
                    'test_responder': {
                        'overwrite': {
                            'd': 'o',
                         },
                        'only_main_config': {
                            'a': 'a',
                            'b': 'b'
                        }
                    }
                }
            }
        }
        return Config(config)

    class TestResponder(ConfigMixin, BaseIdleModule):

        base_default_config = {
            'command_prefix': '.',
            'overwrite': {
                'a': 'a',
                'b': 'b',
                'c': 'c',
                'd': 'd',
             },
            'only_base_default': 'v'
        }

        default_config = {
            'overwrite': {
                'b': 'o',
             },
            'only_default': 'v'
        }

        def __init__(self, config):
            super(TestResponder, self).__init__(config)
            self.register_default_config(self.base_default_config)
            self.register_default_config(self.default_config)
            self.register_config('botnet', 'base_responder')
            self.register_config('testing', 'test_responder')


    t = TestResponder(get_config())

    assert t.config_get('only_main_config.a') == 'a'
    assert t.config_get('only_base_config') == 'v'
    assert t.config_get('only_main_config.b') == 'b'
    assert t.config_get('only_base_default') == 'v'
    assert t.config_get('only_default') == 'v'
    with pytest.raises(ValueError):
        assert t.config_get('only_main_config.b.s') == 'b'
    with pytest.raises(KeyError):
        assert t.config_get('only_main_config.bs') == 'b'

    assert t.config_get('overwrite.a') == 'a'
    assert t.config_get('overwrite.b') == 'o'
    assert t.config_get('overwrite.c') == 'o'
    assert t.config_get('overwrite.d') == 'o'

    t.config_set('new_key.a', 'v')
    assert t.config_get('new_key.a') == 'v'

    t.config_set('new_key.b', [1, 2])
    assert t.config_get('new_key.b') == [1, 2]
    assert t.config_set('new_key.b', [1])
    assert t.config_get('new_key.b') == [1]
    assert t.config_append('new_key.b', 3)
    assert t.config_get('new_key.b') == [1, 3]

    t.config_set('new_key.c', 1)
    with pytest.raises(AttributeError):
        t.config_append('new_key.c', 2)

def test_config_gone():
    def get_config():
        config = {}
        return Config(config)

    class TestResponder(ConfigMixin, BaseIdleModule):
        default_config = {}

        def __init__(self, config):
            super(TestResponder, self).__init__(config)
            self.register_default_config(self.default_config)
            self.register_config('botnet', 'base_responder')
            self.register_config('testing', 'test_responder')

    t = TestResponder(get_config())
    with pytest.raises(KeyError):
        assert t.config_get('k') == 'v'
    assert t.config_set('k', 'v')

    t.config_append('gone', 1)
    assert t.config_get('gone') == [1]

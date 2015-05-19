import pytest
from botnet.config import Config
from botnet.modules import BaseIdleModule
from botnet.modules.mixins import ConfigMixin


def test_default_config():

    class TestResponder(ConfigMixin, BaseIdleModule):

        a = {
            'overwrite': {
                'a': 'a',
                'b': 'b',
             },
            'onlya': 'v'
        }

        b = {
            'overwrite': {
                'b': 'o',
             },
            'onlyb': 'v'
        }

        def __init__(self, config):
            super(TestResponder, self).__init__(config)
            self.register_default_config(self.a)
            self.register_default_config(self.b)


    t = TestResponder(Config())

    # get
    assert t.config_get('onlya') == 'v'
    assert t.config_get('onlyb') == 'v'

    with pytest.raises(ValueError):
        assert t.config_get('onlya.invalid') == 'invalid'
    with pytest.raises(KeyError):
        assert t.config_get('invalid') == 'invalid'

    assert t.config_get('overwrite.a') == 'a'
    assert t.config_get('overwrite.b') == 'o'

    # set
    with pytest.raises(ValueError):
        t.config_set('new_key.a', 'v')


def test_complex_config():
    def get_config():
        config = {
            'modules': ['a', 'b'],
            'module_config': {
                'namespace_a': {
                    'module_name': {
                        'overwrite': {
                            'd': 'invalid',
                            'c': 'o',
                         },
                        'only_namespace_a': 'v'
                    }
                },
                'namespace_b': {
                    'module_name': {
                        'overwrite': {
                            'd': 'o',
                         },
                        'only_namespace_b': 'v'
                    }
                }
            }
        }
        return Config(config)

    class TestResponder(ConfigMixin, BaseIdleModule):

        a = {
            'overwrite': {
                'a': 'a',
                'b': 'b',
                'c': 'c',
                'd': 'd',
             },
            'only_a': 'v'
        }

        b = {
            'overwrite': {
                'b': 'o',
             },
            'only_b': 'v'
        }

        def __init__(self, config):
            super(TestResponder, self).__init__(config)
            self.register_default_config(self.a)
            self.register_default_config(self.b)
            self.register_config('namespace_a', 'module_name')
            self.register_config('namespace_b', 'module_name')


    t = TestResponder(get_config())

    assert t.config_get('only_namespace_a') == 'v'
    assert t.config_get('only_namespace_b') == 'v'
    assert t.config_get('only_a') == 'v'
    assert t.config_get('only_b') == 'v'

    with pytest.raises(ValueError):
        assert t.config_get('overwrite.a.invalid')
    with pytest.raises(KeyError):
        assert t.config_get('overwrite.invalid')

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
    class TestResponder(ConfigMixin, BaseIdleModule):
        a = {}

        def __init__(self, config):
            super(TestResponder, self).__init__(config)
            self.register_default_config(self.a)
            self.register_config('namespace_a', 'module_name')
            self.register_config('namespace_b', 'module_name')

    t = TestResponder(Config())
    with pytest.raises(KeyError):
        assert t.config_get('k') == 'v'
    assert t.config_set('k', 'v')
    assert t.config_get('k') == 'v'

    t.config_append('gone', 1)
    assert t.config_get('gone') == [1]

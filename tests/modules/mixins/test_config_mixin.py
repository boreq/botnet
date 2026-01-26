from dataclasses import dataclass

from botnet.config import Config
from botnet.modules.mixins import ConfigMixin


def test_get_config_with_optional_config_fields_does_not_fail_if_config_is_empty(subtests) -> None:
    @dataclass()
    class TestCase:
        config_data: dict

    test_cases = [
        TestCase(
            config_data={},
        ),
        TestCase(
            config_data={
                'module_config': {
                }
            }
        ),
        TestCase(
            config_data={
                'module_config': {
                    'botnet': {
                    }
                }
            }
        ),
        TestCase(
            config_data={
                'module_config': {
                    'botnet': {
                        'test': {
                        }
                    }
                }
            }
        ),
    ]

    for test_case in test_cases:
        with subtests.test(test_case=test_case):
            @dataclass()
            class TestConfig:
                field: str | None

            class TestConfigMixin(ConfigMixin[TestConfig]):
                config_namespace = 'botnet'
                config_name = 'test'
                config_class = TestConfig

            t = TestConfigMixin(Config(test_case.config_data))
            t.get_config()


def test_updating_empty_config_sets_config_fields_and_sends_a_signal(module_harness_factory) -> None:
    @dataclass()
    class TestConfig:
        field: str | None

    class TestConfigMixin(ConfigMixin[TestConfig]):
        config_namespace = 'botnet'
        config_name = 'test'
        config_class = TestConfig

    t = module_harness_factory.make(TestConfigMixin, Config({}))

    def change_config(config: TestConfig) -> None:
        config.field = 'some value'
    t.module.change_config(change_config)

    assert t.module.get_config() == TestConfig('some value')
    t.expect_config_changed_signals([{}])

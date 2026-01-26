import threading

import pytest

from botnet import modules
from botnet.manager import Manager


def test_stop():
    manager = Manager()

    # Launch Manager.run in a separate thread
    thread = threading.Thread(target=manager.run)
    thread.daemon = True
    thread.start()

    # Check if the manager terminates properly
    manager.stop()
    thread.join(1)
    if thread.is_alive():
        pytest.fail('Manager did not terminate.')


def test_load_module():
    class DummyModule(modules.BaseModule):
        pass

    manager = Manager()

    manager.load_module(DummyModule)
    assert manager._get_wrapper(DummyModule) is not None

    manager.unload_module(DummyModule)
    assert manager._get_wrapper(DummyModule) is None


def test_load_twice():
    class DummyModule(modules.BaseModule):
        pass

    manager = Manager()

    manager.load_module(DummyModule)
    assert manager._get_wrapper(DummyModule) is not None
    assert len(manager.module_wrappers) == 1

    manager.load_module(DummyModule)
    assert manager._get_wrapper(DummyModule) is not None
    assert len(manager.module_wrappers) == 1


def test_load_twice_by_name():
    manager = Manager()

    manager.load_module_by_name('meta')
    assert len(manager.module_wrappers) == 1

    manager.load_module_by_name('meta')
    assert len(manager.module_wrappers) == 1


def test_get_wrapper():
    """Checks if _get_wrapper properly handles inheritance. Ensures that
    a child is not returned when querying for a parent."""
    class DummyModule(modules.BaseModule):
        value = 'parent'

    class DummyModuleChild(DummyModule):
        value = 'child'

    def test(manager):
        parent = manager._get_wrapper(DummyModule)
        child = manager._get_wrapper(DummyModuleChild)
        assert parent.module.value == 'parent'
        assert child.module.value == 'child'

    manager = Manager()
    manager.load_module(DummyModule)
    manager.load_module(DummyModuleChild)
    test(manager)

    manager = Manager()
    manager.load_module(DummyModuleChild)
    manager.load_module(DummyModule)
    test(manager)

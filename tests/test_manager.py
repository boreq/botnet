import pytest
import threading
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
    class DummyIdleModule(modules.BaseIdleModule):
        pass

    class DummyModule(modules.BaseModule):
        pass

    manager = Manager()

    manager.load_module(DummyIdleModule)
    manager.load_module(DummyModule)
    assert manager.get_wrapper(DummyModule) is not None
    assert manager.get_wrapper(DummyIdleModule) is not None

    # Lets actually test if DummyModule will start (and later terminate)
    assert manager.get_wrapper(DummyIdleModule).is_alive()
    assert not manager.get_wrapper(DummyModule).is_alive()
    manager.update()
    assert manager.get_wrapper(DummyModule).is_alive()

    manager.unload_module(DummyIdleModule)
    manager.unload_module(DummyModule)
    assert manager.get_wrapper(DummyModule) is None
    assert manager.get_wrapper(DummyIdleModule) is None


def test_get_wrapper():
    """Checks if get_wrapper properly handles inheritance. Ensures that
    a child is not returned when querying for a parent."""
    class DummyIdleModule(modules.BaseIdleModule):
        value = 'parent'

    class DummyIdleModuleChild(DummyIdleModule):
        value = 'child'

    def test(manager):
        parent = manager.get_wrapper(DummyIdleModule)
        child = manager.get_wrapper(DummyIdleModuleChild)
        assert parent.module.value == 'parent'
        assert child.module.value == 'child'

    manager = Manager()
    manager.load_module(DummyIdleModule)
    manager.load_module(DummyIdleModuleChild)
    test(manager)

    manager = Manager()
    manager.load_module(DummyIdleModuleChild)
    manager.load_module(DummyIdleModule)
    test(manager)

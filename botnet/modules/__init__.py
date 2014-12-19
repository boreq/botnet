import threading


def import_by_name(name):
    """Imports an object from a module. For example if passed name is
    `example.module.thing` this function will return an object called `thing`
    located in `example.module`. This behaviour is similar to normal import
    statement `from example.module import thing`.
    """
    name = name.split('.')
    obj = name[-1]
    module = '.'.join(name[:-1])
    return getattr(__import__(name=module, fromlist=[obj]), obj)


def get_module_class(module_name):
    """Attempts to find a module class by name. This function looks for a
    Python module named `module_name` located in `botnet.modules`. A found Python
    module is expected to contain a variable called `mod` pointing to an actual
    module class. If the name is prefixed with `botnet_` this function will look
    for an external module class instead.
    """
    if not module_name.startswith('botnet_'):
        try:
            import_name = 'botnet.modules.%s.mod' % module_name
            return import_by_name(import_name)
        except ImportError as e:
            pass
    else:
        # TODO: try to load an external module
        pass
    return None


class BaseIdleModule(object):
    """Base module which does not run anything in a loop."""

    def __init__(self, config):
        pass


class BaseModule(BaseIdleModule):
    """Base module with a loop used for periodic updates."""

    deltatime = .016

    def __init__(self, *args, **kwargs):
        super(BaseModule, self).__init__(*args, **kwargs)
        self.stop_event = threading.Event()

    def stop(self):
        self.stop_event.set()

    def run(self):
        self.stop_event.clear()
        while not self.stop_event.is_set():
            self.update()
            self.stop_event.wait(self.deltatime)

    def update(self):
        """This is executed every time deltatime passes."""
        pass

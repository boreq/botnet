import importlib


def get_module(module_name):
    """Attempts to find a bot module by name. This function looks for a
    Python module named `module_name` located in `botnet.modules`. If the name
    is prefixed with `botnet_` this function will look for an external module
    instead.
    """
    if not module_name.startswith('botnet_'):
        import_name = 'botnet.modules.builtin.%s' % module_name
    else:
        import_name = '%s' % module_name
    return importlib.import_module(import_name)


def reload_module(module):
    """Reloads a loaded Python module."""
    importlib.reload(module)


def get_ident_string(module_class):
    """Returns a string which can be used to identify a module class.
    Normal comparison marks the same class as different after reloading it 
    so this string has to be used to compare modules after reloading instead
    of a direct comparison of a type.
    """
    return module_class.__module__ + '.' + module_class.__name__

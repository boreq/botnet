import logging


def get_logger(obj):
    if isinstance(obj, str):
        name = obj
    else:
        name = obj.__class__.__name__
    return logging.getLogger(name)

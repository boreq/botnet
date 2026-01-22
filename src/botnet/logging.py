import logging


Logger = logging.Logger


def get_logger(obj: str | object) -> Logger:
    if isinstance(obj, str):
        name = obj
    else:
        name = obj.__class__.__name__
    return logging.getLogger(name)

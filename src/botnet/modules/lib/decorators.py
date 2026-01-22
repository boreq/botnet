from functools import wraps


def catch_other(exception, default_text):
    """Decorator which catches exceptions which don't inherit from the exception
    class and throws that exception instead.

    exception: exception class.
    default_text: when an exception is replaced the new exception will be
                  initialized with this error message.
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            try:
                return f(*args, **kwargs)
            except exception:
                raise
            except Exception:
                raise exception(default_text)
        return decorated_function
    return decorator

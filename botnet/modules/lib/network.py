"""
    Contains network related utilities which can be used by the modules, for
    example to query various online APIs.
"""

import requests


# User agent used while performing requests (429 status codes can be encountered
# when using the default user agent)
_uagent = 'Mozilla/5.0 (X11; Linux x86_64; rv:34.0) Gecko/20100101 Firefox/34.0'


def get_url(*args, **kwargs):
    """Performs a request. Thin wrapper over requests.request.

    method: request method, defaults to 'GET'.
    """
    method = kwargs.pop('method', None)
    if method is None:
        method = 'GET'
    method = method.upper()

    if not 'headers' in kwargs:
        kwargs['headers'] = {}
    kwargs['headers']['User-Agent'] = _uagent

    return requests.request(method, *args, **kwargs)

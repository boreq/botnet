"""
    Contains network related utilities which can be used by the modules, for
    example to query various online APIs.
"""

import requests

USER_AGENT = 'botnet/1.0 (IRC bot; +https://github.com/boreq/botnet)'


def get_url(*args, **kwargs) -> requests.Response:  # type: ignore
    """Performs a request. Thin wrapper over requests.request.

    method: request method, defaults to 'GET'.
    """
    method = kwargs.pop('method', None)
    if method is None:
        method = 'GET'
    method = method.upper()

    if 'headers' not in kwargs:
        kwargs['headers'] = {}
    kwargs['headers']['User-Agent'] = USER_AGENT

    return requests.request(method, *args, **kwargs)

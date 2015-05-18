import threading
from .helpers import load_json


class Config(dict):
    """A dictionary which provides additional methods to load values from files.

    defaults: default values.
    """

    def __init__(self, defaults=None):
        dict.__init__(self, defaults or {})
        self.lock = threading.Lock()

    def from_json_file(self, file_path):
        self.update(load_json(file_path))

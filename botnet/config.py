import threading
from .helpers import load_json, save_json


class Config(dict):
    """A dictionary which provides additional methods to load values from files.

    defaults: default values.
    """

    def __init__(self, defaults=None):
        dict.__init__(self, defaults or {})
        self.lock = threading.Lock()

    def from_json_file(self, file_path):
        self.update(load_json(file_path))

    def to_json_file(self, file_path):
        save_json(file_path, self, indent=4)

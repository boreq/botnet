import threading
from .helpers import load_json, save_json


class Config(dict):  # type: ignore[type-arg]
    """A dictionary which provides additional methods to load values from files.

    defaults: default values.
    """

    def __init__(self, defaults: dict | None = None) -> None:  # type: ignore[type-arg]
        dict.__init__(self, defaults or {})
        self.lock = threading.Lock()

    def from_json_file(self, file_path: str) -> None:
        # todo I assume this is a bug
        self.update(load_json(file_path))

    def to_json_file(self, file_path: str) -> None:
        save_json(file_path, self, indent=4)

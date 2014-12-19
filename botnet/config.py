import json


class Config(dict):
    """A dictionary which provides additional methods to load values from files.
    
    defaults: default values.
    """

    def __init__(self, defaults=None):
        dict.__init__(self, defaults or {})

    def from_json_file(self, file_path):
        with open(file_path, 'r') as f:
            self.update(json.load(f))

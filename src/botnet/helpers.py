import json
import os
from typing import Any


def load_json(file_path: str) -> Any:
    with open(file_path, 'r') as f:
        return json.load(f)


def save_json(file_path: str, data: Any, **kwargs: Any) -> None:
    tmp_file_path = file_path + '.tmp'
    with open(tmp_file_path, 'w') as f:
        json.dump(data, f, **kwargs)
    os.replace(tmp_file_path, file_path)


def cleanup_nick(nick: str) -> str:
    return nick.lstrip("@+")

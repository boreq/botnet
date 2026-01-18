import json
import os


def load_json(file_path):
    with open(file_path, 'r') as f:
        return json.load(f)


def save_json(file_path, data, **kwargs):
    tmp_file_path = file_path + '.tmp'
    with open(tmp_file_path, 'w') as f:
        json.dump(data, f, **kwargs)
    os.replace(tmp_file_path, file_path)


def is_channel_name(text):
    if text:
        return text[0] in ['&', '#', '+', '!']
    return False


def cleanup_nick(nick):
    return nick.lstrip("@+")

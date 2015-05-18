import json


def load_json(file_path):
    with open(file_path, 'r') as f:
        return json.load(f)


def save_json(file_path, data, **kwargs):
    with open(file_path, 'w') as f:
        json.dump(data, f, **kwargs)


def is_channel_name(text):
    if text:
        return text[0] in ['&', '#', '+', '!']
    return False

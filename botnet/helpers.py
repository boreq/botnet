def is_channel_name(text):
    if text:
        return text[0] in ['&', '#', '+', '!']
    return False

from botnet.modules.lib import divide_text


def test_divide_text() -> None:
    assert divide_text('', 10) == [
        ''
    ]

    assert divide_text('one two three four', 10) == [
        'one two', 'three four',
    ]

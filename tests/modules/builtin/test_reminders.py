import pytest
from botnet.modules.builtin.reminders import parse_message


def test_parse_seconds():
    assert parse_message('11.1s lorem ipsum') == (11.1, 'lorem ipsum')
    assert parse_message('11.1sec lorem ipsum') == (11.1, 'lorem ipsum')
    assert parse_message('11.1second lorem ipsum') == (11.1, 'lorem ipsum')
    assert parse_message('11.1seconds lorem ipsum') == (11.1, 'lorem ipsum')

    assert parse_message('11.1 s lorem ipsum') == (11.1, 'lorem ipsum')
    assert parse_message('11.1 sec lorem ipsum') == (11.1, 'lorem ipsum')
    assert parse_message('11.1 second lorem ipsum') == (11.1, 'lorem ipsum')
    assert parse_message('11.1 seconds lorem ipsum') == (11.1, 'lorem ipsum')


def test_parse_minutes():
    assert parse_message('1.5m lorem ipsum') == (90, 'lorem ipsum')
    assert parse_message('1.5min lorem ipsum') == (90, 'lorem ipsum')
    assert parse_message('1.5mins lorem ipsum') == (90, 'lorem ipsum')
    assert parse_message('1.5minute lorem ipsum') == (90, 'lorem ipsum')
    assert parse_message('1.5minutes lorem ipsum') == (90, 'lorem ipsum')

    assert parse_message('1.5 m lorem ipsum') == (90, 'lorem ipsum')
    assert parse_message('1.5 min lorem ipsum') == (90, 'lorem ipsum')
    assert parse_message('1.5 mins lorem ipsum') == (90, 'lorem ipsum')
    assert parse_message('1.5 minute lorem ipsum') == (90, 'lorem ipsum')
    assert parse_message('1.5 minutes lorem ipsum') == (90, 'lorem ipsum')


def test_parse_hours():
    assert parse_message('1.5h lorem ipsum') == (60 * 60 * 1.5, 'lorem ipsum')
    assert parse_message('1.5hour lorem ipsum') == (60 * 60 * 1.5, 'lorem ipsum')
    assert parse_message('1.5hours lorem ipsum') == (60 * 60 * 1.5, 'lorem ipsum')

    assert parse_message('1.5 h lorem ipsum') == (60 * 60 * 1.5, 'lorem ipsum')
    assert parse_message('1.5 hour lorem ipsum') == (60 * 60 * 1.5, 'lorem ipsum')
    assert parse_message('1.5 hours lorem ipsum') == (60 * 60 * 1.5, 'lorem ipsum')


def test_parse_days():
    assert parse_message('1.5d lorem ipsum') == (60 * 60 * 24 * 1.5, 'lorem ipsum')
    assert parse_message('1.5day lorem ipsum') == (60 * 60 * 24 * 1.5, 'lorem ipsum')
    assert parse_message('1.5days lorem ipsum') == (60 * 60 * 24 * 1.5, 'lorem ipsum')

    assert parse_message('1.5 d lorem ipsum') == (60 * 60 * 24 * 1.5, 'lorem ipsum')
    assert parse_message('1.5 day lorem ipsum') == (60 * 60 * 24 * 1.5, 'lorem ipsum')
    assert parse_message('1.5 days lorem ipsum') == (60 * 60 * 24 * 1.5, 'lorem ipsum')


def test_parse_months():
    assert parse_message('1.5month lorem ipsum') == (60 * 60 * 24 * 30 * 1.5, 'lorem ipsum')
    assert parse_message('1.5months lorem ipsum') == (60 * 60 * 24 * 30 * 1.5, 'lorem ipsum')

    assert parse_message('1.5 month lorem ipsum') == (60 * 60 * 24 * 30 * 1.5, 'lorem ipsum')
    assert parse_message('1.5 months lorem ipsum') == (60 * 60 * 24 * 30 * 1.5, 'lorem ipsum')


def test_parse_years():
    assert parse_message('1.5y lorem ipsum') == (60 * 60 * 24 * 365 * 1.5, 'lorem ipsum')
    assert parse_message('1.5year lorem ipsum') == (60 * 60 * 24 * 365 * 1.5, 'lorem ipsum')
    assert parse_message('1.5years lorem ipsum') == (60 * 60 * 24 * 365 * 1.5, 'lorem ipsum')

    assert parse_message('1.5 y lorem ipsum') == (60 * 60 * 24 * 365 * 1.5, 'lorem ipsum')
    assert parse_message('1.5 year lorem ipsum') == (60 * 60 * 24 * 365 * 1.5, 'lorem ipsum')
    assert parse_message('1.5 years lorem ipsum') == (60 * 60 * 24 * 365 * 1.5, 'lorem ipsum')


def test_parse_no_message():
    with pytest.raises(ValueError):
        parse_message('1.5y')


def test_parse_no_unit():
    with pytest.raises(ValueError):
        parse_message('1.5 lorem ipsum')


def test_parse_no_amount():
    with pytest.raises(ValueError):
        parse_message('y lorem ipsum')

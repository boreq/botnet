from botnet.config import Config
from botnet.modules.builtin.github import GithubAPI, Github
import json


class A(GithubAPI):
    """Loads the response JSON from file and not the actual API."""

    def __init__(self, path):
        super(A, self).__init__()
        self.path = path

    def get_raw_repo_events(self, owner, repo):
        with open(self.path, 'r') as fp:
            content = fp.read()
        return json.loads(content)

class G(Github):

    default_config = {
        "track": [
            {
                "owner": "boreq",
                "repo": "botnet",
                "channels": ["#botnet-dev"]
            }
        ]
    }

    def __init__(self, config):
        super(Github, self).__init__(config)
        self.api = self.api_class()


def test_event_parser(resource_path):
    a = A(resource_path('events.json'))
    a._last_events['boreq/botnet'] = 0

    t = a.get_event_texts('boreq', 'botnet')
    assert len(t) == 6


def test_response(resource_path, msg_t):
    a = A(resource_path('events.json'))
    a._last_events['boreq/botnet'] = 0

    g = G(Config())
    g.api = a

    g.update()
    assert 'commits' in str(msg_t.msg)


def test_admin(rec_admin_msg, make_privmsg):
    g = Github(Config())

    msg = make_privmsg('.github_track owner repo #channel')
    rec_admin_msg(msg)
    assert g.config_get('track')

    msg = make_privmsg('.github_untrack owner repo #channel')
    rec_admin_msg(msg)
    assert not g.config_get('track')


def test_admin_one_left(rec_admin_msg, make_privmsg):
    g = Github(Config())

    msg = make_privmsg('.github_track owner repo #channel1')
    rec_admin_msg(msg)
    assert len(g.config_get('track')[0]['channels']) == 1

    msg = make_privmsg('.github_track owner repo #channel2')
    rec_admin_msg(msg)
    assert len(g.config_get('track')[0]['channels']) == 2

    msg = make_privmsg('.github_untrack owner repo #channel2')
    rec_admin_msg(msg)
    assert len(g.config_get('track')[0]['channels']) == 1


def test_admin_all_gone(rec_admin_msg, make_privmsg):
    g = Github(Config())

    msg = make_privmsg('.github_track owner repo #channel1')
    rec_admin_msg(msg)
    msg = make_privmsg('.github_track owner repo #channel2')
    rec_admin_msg(msg)
    assert len(g.config_get('track')[0]['channels']) == 2

    msg = make_privmsg('.github_untrack owner repo *')
    rec_admin_msg(msg)
    assert not g.config_get('track')


def test_admin_multiple(rec_admin_msg, make_privmsg):
    g = Github(Config())

    msg = make_privmsg('.github_track owner repo1 #channel')
    rec_admin_msg(msg)
    msg = make_privmsg('.github_track owner repo2 #channel')
    rec_admin_msg(msg)
    assert len(g.config_get('track')) == 2

    msg = make_privmsg('.github_untrack owner repo1 #channel')
    rec_admin_msg(msg)
    assert len(g.config_get('track')) == 1

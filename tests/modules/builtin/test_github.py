from botnet.config import Config
from botnet.message import Message
from botnet.modules import AuthContext
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


def test_event_parser(resource_path):
    a = A(resource_path('events.json'))
    a._last_events['boreq/botnet'] = 0

    t = a.get_event_texts('boreq', 'botnet')
    assert len(t) == 6


def test_response(module_harness_factory, resource_path):
    a = A(resource_path('events.json'))
    a._last_events['boreq/botnet'] = 0

    g = module_harness_factory.make(G, Config())
    g.module.api = a

    g.module.update()
    g.expect_message_out_signals(
        [
            {
                'msg': Message.new_from_string('PRIVMSG #botnet-dev :https://github.com/boreq/botnet new events: issue comments created: https://github.com/django/django/pull/4699#issuecomment-106543528 | pull requests: https://github.com/django/django/pull/4665 was closed | 1 commits to refs/heads/master | starred by: kez0r | forked to: https://github.com/grzes/django | issues: https://github.com/Homebrew/homebrew/issues/40102 was closed')
            }
        ]
    )


def test_admin(module_harness_factory, make_incoming_privmsg):
    g = module_harness_factory.make(Github, Config())

    msg = make_incoming_privmsg('.github_track owner repo #channel')
    g.receive_auth_message_in(msg, AuthContext('some-uuid', ['admin']))
    assert g.module.config_get('track')

    msg = make_incoming_privmsg('.github_untrack owner repo #channel')
    g.receive_auth_message_in(msg, AuthContext('some-uuid', ['admin']))
    assert not g.module.config_get('track')


def test_admin_one_left(module_harness_factory, make_incoming_privmsg):
    g = module_harness_factory.make(Github, Config())

    msg = make_incoming_privmsg('.github_track owner repo #channel1')
    g.receive_auth_message_in(msg, AuthContext('some-uuid', ['admin']))
    g.receive_auth_message_in(msg, AuthContext('some-uuid', ['admin']))
    assert len(g.module.config_get('track')[0]['channels']) == 1

    msg = make_incoming_privmsg('.github_track owner repo #channel2')
    g.receive_auth_message_in(msg, AuthContext('some-uuid', ['admin']))
    assert len(g.module.config_get('track')[0]['channels']) == 2

    msg = make_incoming_privmsg('.github_untrack owner repo #channel2')
    g.receive_auth_message_in(msg, AuthContext('some-uuid', ['admin']))
    assert len(g.module.config_get('track')[0]['channels']) == 1


def test_admin_all_gone(module_harness_factory, make_incoming_privmsg):
    g = module_harness_factory.make(Github, Config())

    msg = make_incoming_privmsg('.github_track owner repo #channel1')
    g.receive_auth_message_in(msg, AuthContext('some-uuid', ['admin']))

    msg = make_incoming_privmsg('.github_track owner repo #channel2')
    g.receive_auth_message_in(msg, AuthContext('some-uuid', ['admin']))

    assert len(g.module.config_get('track')[0]['channels']) == 2

    msg = make_incoming_privmsg('.github_untrack owner repo')
    g.receive_auth_message_in(msg, AuthContext('some-uuid', ['admin']))

    assert not g.module.config_get('track')


def test_admin_multiple(module_harness_factory, make_incoming_privmsg):
    g = module_harness_factory.make(Github, Config())

    msg = make_incoming_privmsg('.github_track owner repo1 #channel')
    g.receive_auth_message_in(msg, AuthContext('some-uuid', ['admin']))

    msg = make_incoming_privmsg('.github_track owner repo2 #channel')
    g.receive_auth_message_in(msg, AuthContext('some-uuid', ['admin']))

    assert len(g.module.config_get('track')) == 2

    msg = make_incoming_privmsg('.github_untrack owner repo1 #channel')
    g.receive_auth_message_in(msg, AuthContext('some-uuid', ['admin']))

    assert len(g.module.config_get('track')) == 1

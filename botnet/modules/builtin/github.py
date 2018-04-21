from collections import defaultdict
import threading
from .. import BaseResponder
from ..lib import MemoryCache, get_url, parse_command, catch_other
from ...message import Message
from ...signals import on_exception, message_out, config_changed


class APIError(Exception):
    pass


class EventParser(object):
    """Converts events downloaded from the API into readable texts."""

    def parse_CreateEvent(self, events):
        repos = []
        branches = []
        tags = []

        for event in events:
            if event['payload']['ref_type'] == 'repository':
                repos.append(event['repo']['name'])
            if event['payload']['ref_type'] == 'branch':
                branches.append(event['payload']['ref'])
            if event['payload']['ref_type'] == 'tag':
                branches.append(event['payload']['ref'])

        text = []
        if repos:
            text.append('created repositories: %s' % ', '.join(repos))
        if branches:
            text.append('created branches: %s' % ', '.join(branches))
        if tags:
            text.append('created tags: %s' % ', '.join(tags))
        return text

    def parse_ForkEvent(self, events):
        forks = [e['payload']['forkee']['html_url'] for e in events]
        text = 'forked to: %s' % ', '.join(forks)
        return [text]

    def parse_IssueCommentEvent(self, events):
        comments = [e['payload']['comment']['html_url'] for e in events]
        text = 'issue comments created: %s' % ', '.join(comments)
        return [text]

    def parse_IssuesEvent(self, events):
        actions = []
        for e in events:
            actions.append('%s was %s' % (e['payload']['issue']['html_url'], e['payload']['action']))
        text = 'issues: %s' % ', '.join(actions)
        return [text]

    def parse_PullRequestEvent(self, events):
        actions = []
        for e in events:
            actions.append('%s was %s' % (e['payload']['pull_request']['html_url'], e['payload']['action']))
        text = 'pull requests: %s' % ', '.join(actions)
        return [text]

    def parse_PushEvent(self, events):
        texts = []
        for e in  events:
            text = '%s commits to %s' % (e['payload']['size'], e['payload']['ref'])
            texts.append(text)
        return texts

    def parse_ReleaseEvent(self, events):
        actions = []
        for e in events:
            actions.append('%s was %s' % (e['payload']['release']['html_url'], e['payload']['action']))
        text = 'releases: %s' % ', '.join(actions)
        return [text]

    def parse_WatchEvent(self, events):
        starred_by = [e['actor']['login'] for e in events]
        text = 'starred by: %s' % ', '.join(starred_by)
        return [text]

    def parse(self, event_dict):
        """Call this to convert `event_dict` into a list of human readable
        strings.

        Event dict should contain events of the same type grouped under one key:

            {
                '<event_type>': [ {<event_data}, ... ]
            }

        """
        texts = []
        for event_type, events in event_dict.items():
            f = getattr(self, 'parse_' + event_type, None)
            if f is not None:
                texts.extend(f(events))
        return texts


class GithubAPI(object):

    url_root = 'https://api.github.com'

    def __init__(self):
        self._repo_cache = MemoryCache(default_timeout=600)
        self._user_cache = MemoryCache(default_timeout=600)
        # { '<owner>/<repo>': id of the last processed event }
        self._last_events = {}
        self._ep = EventParser()

    def _get(self, url, **params):
        """Performs an API GET request.

        params: GET request parameters.
        """
        url = self.url_root + url
        try:
            r = get_url(url, params=params)
            r.raise_for_status()
            return r.json()
        except Exception as e:
            raise APIError('API error')

    def search_repositories(self, q):
        rw = self._repo_cache.get(q)
        if rw is None:
            rw = self._get('/search/repositories', q=q)
            self._repo_cache.set(q, rw)
        return  rw

    def search_users(self, q):
        rw = self._user_cache.get(q)
        if rw is None:
            rw = self._get('/search/users', q=q)
            self._user_cache.set(q, rw)
        return  rw

    def get_raw_repo_events(self, owner, repo):
        """Gets the fresh event data directly from the API."""
        return self._get('/repos/%s/%s/events' % (owner, repo))

    def get_new_repo_events(self, owner, repo):
        """Gets the fresh event data directly from the API, selects only
        new ones and puts them in the dictionary."""
        key = '%s/%s' % (owner, repo)
        last_id = self._last_events.get(key, -1)
        highest_id = -1
        events = defaultdict(list)

        d = self.get_raw_repo_events(owner, repo)
        for event in d:
            event['id'] = int(event['id'])
            highest_id = max(highest_id, event['id'])
            if last_id >= 0 and event['id'] > last_id:
                events[event['type']].append(event)

        self._last_events[key] = highest_id
        return events

    def get_event_texts(self, owner, repo):
        """Returns a new array with human readable string about events in the
        repository which occured since the last call to this function with
        the same parameters.
        """
        all_events = self.get_new_repo_events(owner, repo)
        texts = self._ep.parse(all_events)
        return texts


class Github(BaseResponder):
    """Implements Github search and tracks Github repository events.

    Example module config:

        "botnet": {
            "github": {
                "track": [
                    {
                        "owner": "boreq",
                        "repo": "botnet",
                        "channels": ["#botnet-dev"]
                    }
                ]
            }
        }

    """

    config_namespace = 'botnet'
    config_name = 'github'
    api_class = GithubAPI
    deltatime = 300

    def __init__(self, config):
        super().__init__(config)
        self.api = self.api_class()

    def start(self):
        super().start()
        # run the code checking the events in a separate thread
        self.stop_event = threading.Event()
        self.t = threading.Thread(target=self.run)
        self.t.start()

    def stop(self):
        super().stop()
        self.stop_event.set()

    def run(self):
        """Runs in a separate threads to query the event API periodically."""
        while not self.stop_event.is_set():
            try:
                self.update()
                self.stop_event.wait(self.deltatime)
            except Exception as e:
                on_exception.send(self, e=e)

    def update(self):
        """Queries the event API."""
        self.logger.debug('Performing event update')
        for data in self.config_get('track', []):
            try:
                # prepare the text
                texts = self.api.get_event_texts(data['owner'], data['repo'])
                info = 'https://github.com/{owner}/{repo} new events: '.format(
                    owner=data['owner'],
                    repo=data['repo']
                )
                text = info + ' | '.join(texts)
                # send the text
                if texts:
                    for channel in data['channels']:
                        msg = Message(command='PRIVMSG', params=[channel, text])
                        message_out.send(self, msg=msg)
            except Exception as e:
                on_exception.send(self, e=e)

    @catch_other(APIError, 'API error')
    def get_repo(self, phrase):
        r = self.api.search_repositories(phrase)
        return self.get_first(r)

    @catch_other(APIError, 'API error')
    def get_user(self, phrase):
        r = self.api.search_users(phrase)
        return self.get_first(r)

    def get_first(self, r):
        d = r['items']
        if not d:
            raise APIError('No results')
        return d[0]['html_url']

    def in_background(self, f):
        """Launches a function in a separate thread."""
        t = threading.Thread(target=f)
        t.daemon = True
        t.run()

    def config_get_tracking_data(self, owner, repo):
        tracked = self.config_get('track', [])
        for data in tracked:
            if data['owner'] == owner and data['repo'] == repo:
                return data
        return None

    def get_subscription_info_text(self, owner, repo):
        d = self.config_get_tracking_data(owner, repo)
        if d is not None:
            text = 'Channels subscribed to %s/%s: %s' % (owner, repo, ', '.join(d['channels']))
        else:
            text = '%s/%s is not being tracked' % (owner, repo)
        return text

    @parse_command([('owner', 1), ('repo', 1), ('channels', '+')], launch_invalid=False)
    def admin_command_github_track(self, msg, args):
        """Starts tracking a repo. Events from a tracked repository (such as new
        created issues or pushed commits) are sent to the specified channels.
        If the repo is already tracked subscribes additional channels to the
        updates.

        Syntax: github_track OWNER REPO CHANNEL ...
        """
        owner = args.owner[0]
        repo = args.repo[0]

        d = self.config_get_tracking_data(owner, repo)
        if d is not None:
            for channel in args.channels:
                if channel not in d['channels']:
                    d['channels'].append(channel)
            config_changed.send(self)
        else:
            data = {
                'owner': owner,
                'repo': repo,
                'channels': args.channels
            }
            self.config_append('track', data)

        text = self.get_subscription_info_text(owner, repo)
        self.respond(msg, text)

    @parse_command([('owner', 1), ('repo', 1), ('channels', '*')], launch_invalid=False)
    def admin_command_github_untrack(self, msg, args):
        """Unsubscribes a channel from receiving updates about events occuring
        in a repository. If no CHANNELs are passed as an argument all channels
        are unsubscribed from the updates and the repository is in effect no
        longer tracked.

        Syntax: github_untrack OWNER REPO [CHANNEL ...]
        """
        owner = args.owner[0]
        repo = args.repo[0]

        d = self.config_get_tracking_data(owner, repo)
        if d is not None:
            # remove channels
            if not args.channels:
                d['channels'] = []
            else:
                d['channels'] = [c for c in d['channels'] if c not in args.channels]
            # remove entire entry if no channels left
            if not d['channels']:
                self.config_get('track').remove(d)
            config_changed.send(self)
            # info text
            text = 'Channels removed. ' + self.get_subscription_info_text(owner, repo)
            self.respond(msg, text)
        else:
            self.respond(msg, 'This repository is not being tracked')

    def admin_command_github_tracked(self, msg):
        """Lists tracked repositories.

        Syntax: github_tracked
        """
        texts = []
        for data in self.config_get('track', []):
            texts.append('{owner}/{repo}: {channels}'.format(
                owner=data['owner'],
                repo=data['repo'],
                channels=', '.join(data['channels']))
            )
        if texts:
            text = ' | '.join(texts)
        else:
            text = 'No tracked repositories'
        self.respond(msg, text)

    @parse_command([('phrase', '+')], launch_invalid=False)
    def command_github(self, msg, args):
        """Search Github repositories.

        Syntax: github PHRASE
        """
        phrase = ' '.join(args.phrase)
        def f():
            try:
                r = self.get_repo(phrase)
                self.respond(msg, r)
            except Exception as e:
                self.respond(msg, str(e))
        self.in_background(f)

    @parse_command([('phrase', '+')], launch_invalid=False)
    def command_github_user(self, msg, args):
        """Search Github users.

        Syntax: github_user PHRASE
        """
        phrase = ' '.join(args.phrase)
        def f():
            try:
                r = self.get_user(phrase)
                self.respond(msg, r)
            except Exception as e:
                self.respond(msg, str(e))
        self.in_background(f)


mod = Github

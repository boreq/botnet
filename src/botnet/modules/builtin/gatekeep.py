import datetime
import random
import os
import threading
import dacite
from typing import Any, cast
from collections import namedtuple
from dataclasses import dataclass, asdict
from ...helpers import save_json, load_json, is_channel_name, cleanup_nick
from ...signals import message_out
from ...message import Message
from .. import BaseResponder, predicates, command
from ..lib import MemoryCache, parse_command
from .auth import AuthContext
from ..base import BaseModule


DeferredAction = namedtuple('DeferredAction', ['channel', 'on_complete'])


class NamesMixin(BaseModule):
    """Provides a way of requesting and handling names that are in the channel."""

    cache_timeout = 60

    def __init__(self, config) -> None:
        super().__init__(config)
        self._cache = MemoryCache(self.cache_timeout)
        self._deferred: list[DeferredAction] = []
        self._current: dict[str, list[str]] = {}

    def handler_rpl_namreply(self, msg) -> None:
        """Names reply."""
        channel = msg.params[2]
        if channel not in self._current:
            self._current[channel] = []
        self._current[channel].extend([cleanup_nick(v) for v in msg.params[3].split(' ')])

    def handler_rpl_endofnames(self, msg) -> None:
        """End of WHOIS."""
        if msg.params[1] not in self._current:
            return
        self._cache.set(msg.params[1], self._current.pop(msg.params[1]))
        self._run_deferred()

    def request_names(self, channel, on_complete) -> None:
        """Schedules an action to be completed when the names for the channel
        are available.

        channel: channel to query
        on_complete: function which will be called when the names will be
                     available. Required function signature:
                     void (*function)(list of nicks)
        """
        names = self._cache.get(channel)
        if names is not None:
            on_complete(names)
        else:
            data = DeferredAction(channel, on_complete)
            self._deferred.append(data)
            self._request(data.channel)

    def _run_deferred(self) -> None:
        """Loops over the deferred functions and launches those for which NAMES
        data is available.
        """
        for i in reversed(range(len(self._deferred))):
            d = self._deferred[i]
            data = self._cache.get(d.channel)
            if data is not None:
                d.on_complete(data)
                self._deferred.pop(i)

    def _request(self, channel) -> None:
        """Sends a message with the NAMES command."""
        msg = Message(command='NAMES', params=[channel])
        message_out.send(self, msg=msg)

    def handle_msg(self, msg) -> None:
        # Dispatch to the handlers
        code = msg.command_code()
        if code is not None:
            handler_name = 'handler_%s' % code.name.lower()
        else:
            handler_name = 'handler_%s' % msg.command.lower()
        func = getattr(self, handler_name, None)
        if func is not None:
            func(msg)


def _is_authorised_has_uuid_and_sent_a_privmsg():
    def predicate(module: Any, msg: Message, auth: AuthContext) -> bool:
        authorised_group = module.config_get('authorised_group')
        if authorised_group not in auth.groups:
            return False

        if not auth.uuid:
            return False

        if is_channel_name(msg.params[0]):
            return False

        return True

    return predicates([predicate])


class Gatekeep(NamesMixin, BaseResponder):
    """Allows users to see when was the last time someone said something.

    Example module config:

        "botnet": {
            "gatekeep": {
                "data": "/path/to/data_file.json",
                "channel": "#channel",
                "authorised_group": "somegroup",
                "people": [
                    {
                        "nicks": [
                            "nick"
                        ],
                        "whitelist": true
                    }
                ]
            }
        }

    """

    config_namespace = 'botnet'
    config_name = 'gatekeep'

    store: Store

    def __init__(self, config) -> None:
        super().__init__(config)
        self.store = Store(lambda: self.config_get('data'))

    def handle_privmsg(self, msg: Message) -> None:
        if is_channel_name(msg.params[0]) and msg.params[0] == self.config_get('channel'):
            self.store.on_privmsg(msg.nickname)

    @command('gatekeep')
    @_is_authorised_has_uuid_and_sent_a_privmsg()
    def auth_command_gatekeep(self, msg: Message, auth: AuthContext) -> None:
        """Prints a report containing the number of endorsements and other information.

        Syntax: gatekeep
        """

        def on_complete(names) -> None:
            report = self.store.generate_minority_report(names)

            not_endorsed: list[PersonaReport] = []
            for persona_report in report.persona_reports:
                if auth.uuid in persona_report.endorsements:
                    continue
                not_endorsed.append(persona_report)

            self.respond(msg, 'Everyone: {}'.format(', '.join([v.for_display() for v in reversed(report.persona_reports)])))
            self.respond(msg, 'People who were NOT endorsed by you: {}'.format(', '.join([v.for_display() for v in reversed(not_endorsed)])))
            self.respond(msg, 'If you would like to endorse anyone then you can privately use the \'endorse NICK\' command in this buffer. Please note that this isn\'t a big decision as you can easily reverse it with \'unendorse NICK\'.')

        self.request_names(self.config_get('channel'), on_complete)

    @command('endorse')
    @_is_authorised_has_uuid_and_sent_a_privmsg()
    @parse_command([('nick', 1)])
    def auth_command_endorse(self, msg: Message, auth: AuthContext, args) -> None:
        """Adds your endorsement for a nick.

        Syntax: endorse NICK
        """
        def on_complete(names) -> None:
            nick = cleanup_nick(args.nick[0])
            if nick in names:
                self.store.endorse(auth, nick)
                self.respond(msg, 'You endorsed {}!'.format(nick))
            else:
                self.respond(msg, 'There is no {} in the channel.'.format(nick))

        self.request_names(self.config_get('channel'), on_complete)

    @command('unendorse')
    @_is_authorised_has_uuid_and_sent_a_privmsg()
    @parse_command([('nick', 1)])
    def auth_command_unendorse(self, msg: Message, auth: AuthContext, args) -> None:
        """Removes your endorsement for a nick.

        Syntax: unendorse NICK
        """
        nick = cleanup_nick(args.nick[0])
        if self.store.unendorse(auth, nick):
            self.respond(msg, 'You unendorsed {}!'.format(nick))
        else:
            self.respond(msg, 'You never endorsed {}.'.format(nick))

    @command('merge_personas')
    @_is_authorised_has_uuid_and_sent_a_privmsg()
    @parse_command([('nick1', 1), ('nick2', 1)])
    def auth_command_merge_personas(self, msg: Message, auth: AuthContext, args) -> None:
        """Merges two personas (use if one physical person has multiple clients in the channel).

        Syntax: merge_personas NICK1 NICK2
        """
        nick1 = cleanup_nick(args.nick1[0])
        nick2 = cleanup_nick(args.nick2[0])

        def on_complete(names) -> None:
            if nick1 in names and nick2 in names:
                self.store.merge_personas(nick1, nick2)
                self.respond(msg, 'You merged {} and {}!'.format(nick1, nick2))
            else:
                self.respond(msg, 'At least one of those nicks isn\'t in the channel!')

        self.request_names(self.config_get('channel'), on_complete)


class Store(object):

    def __init__(self, path):
        self.lock = threading.Lock()
        self._set_path(path)
        self._state = State([], {})
        self._load()

    def on_privmsg(self, nick: str) -> None:
        with self.lock:
            self._state.on_privmsg(nick)
            self._save()

    def endorse(self, endorser: AuthContext, endorsee_nick: str) -> None:
        with self.lock:
            self._state.endorse(endorser, endorsee_nick)
            self._save()

    def unendorse(self, unendorser: AuthContext, unendorsee_nick: str) -> bool:
        with self.lock:
            rv = self._state.unendorse(unendorser, unendorsee_nick)
            self._save()
            return rv

    def merge_personas(self, nick1: str, nick2: str) -> None:
        with self.lock:
            self._state.merge_personas(nick1, nick2)
            self._save()

    def generate_minority_report(self, nicks: list[str]) -> MinorityReport:
        with self.lock:
            return MinorityReport.generate(self._state, nicks)

    def _set_path(self, path):
        with self.lock:
            self._path = path

    def _load(self):
        if os.path.isfile(self._path()):
            try:
                j = load_json(self._path())
                self._state = dacite.from_dict(data_class=State, data=j)
            except:
                self._state = State({})

    def _save(self) -> None:
        save_json(self._path(), asdict(self._state))


@dataclass
class State:
    personas: list[Persona]
    nick_infos: dict[str, NickInfo]

    def on_privmsg(self, nick):
        if nick not in self.nick_infos:
            self.nick_infos[nick] = NickInfo.new_due_to_privmsg()
            return
        self.nick_infos[nick].on_privmsg()

    def endorse(self, endorser: AuthContext, endorsee_nick: str) -> None:
        if endorsee_nick not in self.nick_infos:
            self.nick_infos[endorsee_nick] = NickInfo.new_due_to_endorsement(endorser)
            return
        self.nick_infos[endorsee_nick].endorse(endorser)

    def unendorse(self, unendorser: AuthContext, unendorsee_nick: str) -> bool:
        if unendorsee_nick not in self.nick_infos:
            return False
        return self.nick_infos[unendorsee_nick].unendorse(unendorser)

    def merge_personas(self, nick1: str, nick2: str) -> None:
        for persona in self.personas:
            if nick1 in persona.nicks or nick2 in persona.nicks:
                persona.add_nick(nick1)
                persona.add_nick(nick2)
                return
        self.personas.append(Persona.new(nick1, nick2))

    def all_nicks_of(self, nick: str) -> list[str]:
        all_nicks = set([nick])
        for persona in self.personas:
            if nick in persona.nicks:
                all_nicks.update(persona.nicks)
        return list(all_nicks)

    def get_endorsements(self, nick: str) -> list[str]:
        all_nicks = self.all_nicks_of(nick)
        endorsements: set[str] = set()
        for possible_nick in all_nicks:
            info = self.nick_infos.get(possible_nick)
            if info is not None:
                endorsements.update(info.endorsements)
        return list(endorsements)


@dataclass
class Persona:
    nicks: list[str]

    @classmethod
    def new(cls, nick1: str, nick2: str) -> Persona:
        return cls([nick1, nick2])

    def add_nick(self, nick: str) -> None:
        if nick not in self.nicks:
            self.nicks.append(nick)


@dataclass
class NickInfo:
    first_message: None | float
    last_message: None | float
    endorsements: list[str]

    @classmethod
    def new_due_to_privmsg(cls) -> NickInfo:
        return cls(datetime.datetime.now().timestamp(), datetime.datetime.now().timestamp(), [])

    @classmethod
    def new_due_to_endorsement(cls, endorser: AuthContext) -> NickInfo:
        assert endorser.uuid is not None
        return cls(None, None, [cast(str, endorser.uuid)])

    def on_privmsg(self) -> None:
        if self.first_message is None:
            self.first_message = datetime.datetime.now().timestamp()
        self.last_message = datetime.datetime.now().timestamp()

    def endorse(self, endorser: AuthContext) -> None:
        assert endorser.uuid is not None
        if endorser.uuid not in self.endorsements:
            self.endorsements.append(endorser.uuid)

    def unendorse(self, unendorser: AuthContext) -> bool:
        if unendorser.uuid in self.endorsements:
            self.endorsements = [endorser for endorser in self.endorsements if endorser != unendorser.uuid]
            return True
        return False


@dataclass
class MinorityReport:
    persona_reports: list[PersonaReport]

    @classmethod
    def generate(cls, state: State, nicks: list[str]) -> MinorityReport:
        report = cls([])

        for nick in nicks:
            existing = report._find_existing_persona_report(state, nick)
            if existing is not None:
                existing.add_nick(nick)
            else:
                new = PersonaReport.new(state, nick)
                report.persona_reports.append(new)

        random.shuffle(report.persona_reports)
        report.persona_reports.sort(key=lambda x: len(x.endorsements))

        return report

    def _find_existing_persona_report(self, state: State, nick: str) -> PersonaReport | None:
        all_nicks = state.all_nicks_of(nick)
        for persona_report in self.persona_reports:
            for possible_nick in all_nicks:
                if possible_nick in persona_report.nicks:
                    return persona_report
        return None


@dataclass
class PersonaReport:
    nicks: list[str]
    endorsements: list[str]

    @classmethod
    def new(cls, state: State, nick: str) -> PersonaReport:
        return PersonaReport([nick], state.get_endorsements(nick))

    def add_nick(self, nick: str) -> None:
        self.nicks.append(nick)

    def for_display(self) -> str:
        return '{} ({})'.format('/'.join(self.nicks), len(self.endorsements))


mod = Gatekeep

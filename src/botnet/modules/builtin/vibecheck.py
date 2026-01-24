import os
import threading
import dacite
from datetime import datetime
from typing import Any, Callable
from dataclasses import dataclass, asdict
from ...helpers import save_json, load_json, cleanup_nick
from ...signals import message_out, on_exception
from ...message import Message, IncomingPrivateMessage, Nick, Channel
from .. import BaseResponder, predicates, command, AuthContext, parse_command, Args
from ..lib import MemoryCache, colored, Color
from ..base import BaseModule
from ...config import Config


@dataclass
class DeferredAction:
    channel: Channel
    on_names_available: Callable[[list[Nick]], None]


_PESTER_IF_NOT_PESTERED_FOR = 60 * 60 * 24 * 7  # [s]
_PESTER_IF_NO_COMMAND_FOR = 60 * 60 * 24 * 1  # [s]


class NamesMixin(BaseModule):
    """Provides a way of requesting and handling names that are in the channel."""

    cache_timeout = 60

    def __init__(self, config: Config) -> None:
        super().__init__(config)
        self._cache: MemoryCache[Channel, list[Nick]] = MemoryCache(self.cache_timeout)
        self._deferred: list[DeferredAction] = []
        self._current: dict[Channel, list[Nick]] = {}

    def handler_rpl_namreply(self, msg: Message) -> None:
        """Names reply."""
        channel = Channel(msg.params[2])
        if channel not in self._current:
            self._current[channel] = []
        self._current[channel].extend([Nick(cleanup_nick(v)) for v in msg.params[3].split(' ')])

    def handler_rpl_endofnames(self, msg: Message) -> None:
        """End of WHOIS."""
        channel = Channel(msg.params[1])
        if channel not in self._current:
            return
        self._cache.set(channel, self._current.pop(channel))
        self._run_deferred()

    def request_names(self, channel: Channel, on_names_available: Callable[[list[Nick]], None]) -> None:
        """Schedules an action to be completed when the names for the channel
        are available.

        channel: channel to query
        on_names_available: function which will be called when the names will be
                     available. Required function signature:
                     void (*function)(list of nicks)
        """
        names = self._cache.get(channel)
        if names is not None:
            on_names_available(names)
        else:
            data = DeferredAction(channel, on_names_available)
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
                d.on_names_available(data)
                self._deferred.pop(i)

    def _request(self, channel: Channel) -> None:
        """Sends a message with the NAMES command."""
        msg = Message(command='NAMES', params=[channel.s])
        message_out.send(self, msg=msg)

    def handle_msg(self, msg: Message) -> None:
        # Dispatch to the handlers
        code = msg.command_code
        if code is not None:
            handler_name = 'handler_%s' % code.name.lower()
        else:
            handler_name = 'handler_%s' % msg.command.lower()
        func = getattr(self, handler_name, None)
        if func is not None:
            func(msg)


def _is_authorised_has_uuid_and_sent_a_privmsg():
    def predicate(module: Any, msg: IncomingPrivateMessage, auth: AuthContext) -> bool:
        authorised_group = module.config_get('authorised_group')
        if authorised_group not in auth.groups:
            return False

        if not auth.uuid:
            return False

        if msg.target.is_channel:
            return False

        return True

    return predicates([predicate])


class Vibecheck(NamesMixin, BaseResponder):
    """Vibecheck enables people to better keep track of who's in a channel and if they are someone who people know or
    not.

    Example module config:

        "botnet": {
            "vibecheck": {
                "data": "/path/to/data_file.json",
                "channel": "#channel",
                "authorised_group": "somegroup",
            }
        }

    """

    config_namespace = 'botnet'
    config_name = 'vibecheck'
    store: Store
    maybe_pester_people_every = 60 * 15  # [s]

    def __init__(self, config: Config) -> None:
        super().__init__(config)
        self._store = Store(lambda: self.config_get('data'))
        self._stop_event = threading.Event()
        self._t = threading.Thread(target=self.run)
        self._t.start()

    @command('vibecheck')
    @_is_authorised_has_uuid_and_sent_a_privmsg()
    def auth_command_vibecheck(self, msg: IncomingPrivateMessage, auth: AuthContext) -> None:
        """Prints a report containing the number of endorsements and other information. This command works only in
        direct messages.

        Syntax: vibecheck
        """
        command_prefix = self.get_command_prefix()

        def on_names_available(names: list[Nick]) -> None:
            assert auth.uuid is not None

            with self._store as state:
                report = state.generate_report(auth.uuid, names)

            self.respond(msg, 'Everyone currently in the channel: {}'.format(', '.join([v.for_display(auth.uuid) for v in reversed(report.persona_reports)])))
            self.respond(msg, f'If you would like to endorse anyone then you can privately use the \'{command_prefix}endorse NICK\' command in this buffer. Please note that this isn\'t a big decision as you can easily reverse it with \'{command_prefix}unendorse NICK\'.')

        channel = Channel(self.config_get('channel'))
        self.request_names(channel, on_names_available)

    @command('endorse')
    @_is_authorised_has_uuid_and_sent_a_privmsg()
    @parse_command([('nick', '+')])
    def auth_command_endorse(self, msg: IncomingPrivateMessage, auth: AuthContext, args: Args) -> None:
        """Adds your endorsement for a nick. This command works only in direct messages.

        Syntax: endorse NICK...
        """
        def on_names_available(names: list[Nick]) -> None:
            assert auth.uuid is not None

            for nick_argument in args['nick']:
                nick = Nick(cleanup_nick(nick_argument))
                if nick in names:
                    with self._store as state:
                        state.endorse(auth.uuid, nick)
                    self.respond(msg, 'You endorsed {}!'.format(nick))
                else:
                    self.respond(msg, 'There is no {} in the channel.'.format(nick))

        channel = Channel(self.config_get('channel'))
        self.request_names(channel, on_names_available)

    @command('unendorse')
    @_is_authorised_has_uuid_and_sent_a_privmsg()
    @parse_command([('nick', '+')])
    def auth_command_unendorse(self, msg: IncomingPrivateMessage, auth: AuthContext, args: Args) -> None:
        """Removes your endorsement for a nick. This command works only in direct messages.

        Syntax: unendorse NICK...
        """
        assert auth.uuid is not None

        for nick_argument in args['nick']:
            nick = Nick(cleanup_nick(nick_argument))
            with self._store as state:
                unendorsed = state.unendorse(auth.uuid, nick)
            if unendorsed:
                self.respond(msg, 'You unendorsed {}!'.format(nick))
            else:
                self.respond(msg, 'You never endorsed {}.'.format(nick))

    @command('merge_personas')
    @_is_authorised_has_uuid_and_sent_a_privmsg()
    @parse_command([('nick1', 1), ('nick2', 1)])
    def auth_command_merge_personas(self, msg: IncomingPrivateMessage, auth: AuthContext, args: Args) -> None:
        """Merges two personas (use if one physical person has multiple clients in the channel). This command works
        only in direct messages.

        Syntax: merge_personas NICK1 NICK2
        """
        nick1 = Nick(cleanup_nick(args['nick1'][0]))
        nick2 = Nick(cleanup_nick(args['nick2'][0]))

        def on_names_available(names: list[Nick]) -> None:
            assert auth.uuid is not None

            if nick1 in names and nick2 in names:
                with self._store as state:
                    state.merge_personas(auth.uuid, nick1, nick2)
                self.respond(msg, 'You merged {} and {}!'.format(nick1, nick2))
            else:
                self.respond(msg, 'At least one of those nicks isn\'t in the channel!')

        channel = Channel(self.config_get('channel'))
        self.request_names(channel, on_names_available)

    def handle_privmsg(self, msg: IncomingPrivateMessage) -> None:
        channel = msg.target.channel
        if channel is not None:
            if channel == Channel(self.config_get('channel')):
                with self._store as state:
                    state.on_privmsg(msg.sender)

    def stop(self) -> None:
        super().stop()
        self._stop_event.set()
        self._t.join()

    def run(self) -> None:
        while not self._stop_event.is_set():
            try:
                self._maybe_pester_people()
                self._stop_event.wait(self.maybe_pester_people_every)
            except Exception as e:
                on_exception.send(self, e=e)

    def _maybe_pester_people(self) -> None:
        command_prefix = self.get_command_prefix()

        def on_names_available(names: list[Nick]) -> None:
            authorised_group = self.config_get('authorised_group')
            for person in self.peek_loaded_config_for_module('botnet', 'auth', 'people', default=[]):
                if authorised_group in person['groups']:
                    with self._store as state:
                        report = state.generate_pestering_report(person['uuid'], names)
                    if report is not None:
                        for nick in person['contact']:
                            self.message(nick, 'Skybird, this is Dropkick with a red dash alpha message in two parts. Break. Break. Stand by to copy the list of people who are currently in the channel:')
                            self.message(nick, ', '.join([v.for_display(person['uuid']) for v in reversed(report.persona_reports)]))
                            self.message(nick, f'If you would like to endorse any of them then you can privately use the \'{command_prefix}endorse NICK\' command in this buffer. Please note that this isn\'t a big decision as you can easily reverse it with \'{command_prefix}unendorse NICK\'. If you want to see the full report use the \'{command_prefix}vibecheck\' command.')

        channel = Channel(self.config_get('channel'))
        self.request_names(channel, on_names_available)


class Store:

    def __init__(self, path: Callable[[], str]) -> None:
        self._lock = threading.Lock()
        self._path = path
        self._state = State({}, [], {})
        self._load()

    def __enter__(self) -> State:
        self._lock.acquire()
        return self._state

    def __exit__(self, exc_type: Any, exc_value: Any, exc_traceback: Any) -> None:
        if exc_type is None and exc_value is None and exc_traceback is None:
            self._save()
        self._lock.release()

    def _load(self) -> None:
        if os.path.isfile(self._path()):
            j = load_json(self._path())
            self._state = dacite.from_dict(data_class=TransportState, data=j).to()

    def _save(self) -> None:
        save_json(self._path(), asdict(TransportState.create(self._state)))


@dataclass
class State:
    authorised_people_infos: dict[str, AuthorisedPersonInfo]
    personas: list[Persona]
    nick_infos: dict[Nick, NickInfo]

    def on_privmsg(self, nick: Nick) -> None:
        if nick not in self.nick_infos:
            self.nick_infos[nick] = NickInfo.new_due_to_privmsg()
            return
        self.nick_infos[nick].on_privmsg()

    def endorse(self, endorser_uuid: str, endorsee_nick: Nick) -> None:
        self._mark_command_executed(endorser_uuid)
        if endorsee_nick not in self.nick_infos:
            self.nick_infos[endorsee_nick] = NickInfo.new_due_to_endorsement(endorser_uuid)
        else:
            self.nick_infos[endorsee_nick].endorse(endorser_uuid)

    def unendorse(self, unendorser_uuid: str, unendorsee_nick: Nick) -> bool:
        self._mark_command_executed(unendorser_uuid)
        if unendorsee_nick not in self.nick_infos:
            return False
        return self.nick_infos[unendorsee_nick].unendorse(unendorser_uuid)

    def merge_personas(self, auth_uuid: str, nick1: Nick, nick2: Nick) -> None:
        self._mark_command_executed(auth_uuid)
        for persona in self.personas:
            if nick1 in persona.nicks or nick2 in persona.nicks:
                persona.add_nick(nick1)
                persona.add_nick(nick2)
                return
        self.personas.append(Persona.new(nick1, nick2))

    def generate_report(self, auth_uuid: str, nicks: list[Nick]) -> MinorityReport:
        self._mark_command_executed(auth_uuid)
        return MinorityReport.generate(self, nicks)

    def generate_pestering_report(self, auth_uuid: str, nicks: list[Nick]) -> MinorityReport | None:
        if auth_uuid in self.authorised_people_infos:
            if not self.authorised_people_infos[auth_uuid].should_pester():
                return None
        self._mark_pestered(auth_uuid)
        return MinorityReport.generate(self, nicks)

    def _all_nicks_of(self, nick: Nick) -> list[Nick]:
        all_nicks = set([nick])
        for persona in self.personas:
            if nick in persona.nicks:
                all_nicks.update(persona.nicks)
        return list(all_nicks)

    def _get_endorsements(self, nick: Nick) -> list[str]:
        all_nicks = self._all_nicks_of(nick)
        endorsements: set[str] = set()
        for possible_nick in all_nicks:
            info = self.nick_infos.get(possible_nick)
            if info is not None:
                endorsements.update(info.endorsements)
        return list(endorsements)

    def _mark_command_executed(self, auth_uuid: str) -> None:
        if auth_uuid not in self.authorised_people_infos:
            self.authorised_people_infos[auth_uuid] = AuthorisedPersonInfo.new_due_to_command_execution()
            return
        self.authorised_people_infos[auth_uuid].update_due_to_command_execution()

    def _mark_pestered(self, auth_uuid: str) -> None:
        if auth_uuid not in self.authorised_people_infos:
            self.authorised_people_infos[auth_uuid] = AuthorisedPersonInfo.new_due_to_pestering()
            return
        self.authorised_people_infos[auth_uuid].update_due_to_pestering()


@dataclass
class Persona:
    nicks: list[Nick]

    @classmethod
    def new(cls, nick1: Nick, nick2: Nick) -> Persona:
        return cls([nick1, nick2])

    def add_nick(self, nick: Nick) -> None:
        if nick not in self.nicks:
            self.nicks.append(nick)


@dataclass
class NickInfo:
    first_message: None | datetime
    last_message: None | datetime
    endorsements: list[str]

    @classmethod
    def new_due_to_privmsg(cls) -> NickInfo:
        return cls(datetime.now(), datetime.now(), [])

    @classmethod
    def new_due_to_endorsement(cls, endorser_uuid: str) -> NickInfo:
        return cls(None, None, [endorser_uuid])

    def on_privmsg(self) -> None:
        if self.first_message is None:
            self.first_message = datetime.now()
        self.last_message = datetime.now()

    def endorse(self, endorser_uuid: str) -> None:
        if endorser_uuid not in self.endorsements:
            self.endorsements.append(endorser_uuid)

    def unendorse(self, unendorser_uuid: str) -> bool:
        if unendorser_uuid in self.endorsements:
            self.endorsements = [endorser for endorser in self.endorsements if endorser != unendorser_uuid]
            return True
        return False


@dataclass
class AuthorisedPersonInfo:
    last_pestered_at: None | datetime
    last_command_executed_at: None | datetime

    @classmethod
    def new_due_to_pestering(cls) -> AuthorisedPersonInfo:
        return cls(datetime.now(), None)

    @classmethod
    def new_due_to_command_execution(cls) -> AuthorisedPersonInfo:
        return cls(None, datetime.now())

    def update_due_to_pestering(self) -> None:
        self.last_pestered_at = datetime.now()

    def update_due_to_command_execution(self) -> None:
        self.last_command_executed_at = datetime.now()

    def should_pester(self) -> bool:
        now = datetime.now().timestamp()

        if self.last_pestered_at is not None:
            seconds_since_pestering = now - self.last_pestered_at.timestamp()
            if seconds_since_pestering < _PESTER_IF_NOT_PESTERED_FOR:
                return False

        if self.last_command_executed_at is not None:
            seconds_since_executing_a_command = now - self.last_command_executed_at.timestamp()
            if seconds_since_executing_a_command < _PESTER_IF_NO_COMMAND_FOR:
                return False

        return True


@dataclass
class MinorityReport:
    persona_reports: list[PersonaReport]

    @classmethod
    def generate(cls, state: State, nicks: list[Nick]) -> MinorityReport:
        report = cls([])

        for nick in nicks:
            existing = report._find_existing_persona_report(state, nick)
            if existing is not None:
                existing.add_nick(nick)
            else:
                new = PersonaReport.new(state, nick)
                report.persona_reports.append(new)

        report.persona_reports.sort(key=lambda x: (len(x.endorsements), x.nicks[0]))

        return report

    def _find_existing_persona_report(self, state: State, nick: Nick) -> PersonaReport | None:
        all_nicks = state._all_nicks_of(nick)
        for persona_report in self.persona_reports:
            for possible_nick in all_nicks:
                if possible_nick in persona_report.nicks:
                    return persona_report
        return None


@dataclass
class PersonaReport:
    nicks: list[Nick]
    endorsements: list[str]

    @classmethod
    def new(cls, state: State, nick: Nick) -> PersonaReport:
        return PersonaReport([nick], state._get_endorsements(nick))

    def add_nick(self, nick: Nick) -> None:
        self.nicks.append(nick)

    def for_display(self, uuid: str) -> str:
        endorsed = uuid in self.endorsements
        nicks = '/'.join([v.s for v in self.nicks])
        if endorsed:
            nicks = colored(nicks, Color.GREEN)
        else:
            nicks = colored(nicks, Color.RED)
        return '{} ({})'.format(nicks, '^' if endorsed else '?')


@dataclass
class TransportState:
    authorised_people_infos: dict[str, TransportAuthorisedPersonInfo]
    personas: list[TransportPersona]
    nick_infos: dict[str, TransportNickInfo]

    @classmethod
    def create(cls, state: State) -> TransportState:
        return TransportState(
            {k: TransportAuthorisedPersonInfo.create(v) for k, v in state.authorised_people_infos.items()},
            [TransportPersona.create(v) for v in state.personas],
            {k.s: TransportNickInfo.create(v) for k, v in state.nick_infos.items()},
        )

    def to(self) -> State:
        authorised_people_infos = {k: v.to() for k, v in self.authorised_people_infos.items()}
        personas = [v.to() for v in self.personas]
        nick_infos = {Nick(k): v.to() for k, v in self.nick_infos.items()}
        return State(authorised_people_infos, personas, nick_infos)


@dataclass
class TransportPersona:
    nicks: list[str]

    @classmethod
    def create(cls, v: Persona) -> TransportPersona:
        return cls(
            [nick.s for nick in v.nicks]
        )

    def to(self) -> Persona:
        return Persona([Nick(v) for v in self.nicks])


@dataclass
class TransportNickInfo:
    first_message: None | float
    last_message: None | float
    endorsements: list[str]

    @classmethod
    def create(cls, v: NickInfo) -> TransportNickInfo:
        return cls(
            v.first_message.timestamp() if v.first_message is not None else None,
            v.last_message.timestamp() if v.last_message is not None else None,
            v.endorsements,
        )

    def to(self) -> NickInfo:
        return NickInfo(
            datetime.fromtimestamp(self.first_message) if self.first_message is not None else None,
            datetime.fromtimestamp(self.last_message) if self.last_message is not None else None,
            self.endorsements,
        )


@dataclass
class TransportAuthorisedPersonInfo:
    last_pestered_at: None | float
    last_command_executed_at: None | float

    @classmethod
    def create(cls, v: AuthorisedPersonInfo) -> TransportAuthorisedPersonInfo:
        return cls(
            v.last_pestered_at.timestamp() if v.last_pestered_at is not None else None,
            v.last_command_executed_at.timestamp() if v.last_command_executed_at is not None else None,
        )

    def to(self) -> AuthorisedPersonInfo:
        return AuthorisedPersonInfo(
            datetime.fromtimestamp(self.last_pestered_at) if self.last_pestered_at is not None else None,
            datetime.fromtimestamp(self.last_command_executed_at) if self.last_command_executed_at is not None else None,
        )


mod = Vibecheck

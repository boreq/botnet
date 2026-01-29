import os
import threading
from dataclasses import asdict
from dataclasses import dataclass
from datetime import datetime
from typing import Any
from typing import Callable

import dacite

from botnet.modules import join_message_handler
from botnet.modules import kick_message_handler
from botnet.modules import part_message_handler
from botnet.modules import quit_message_handler

from ...codes import Code
from ...config import Config
from ...helpers import cleanup_nick
from ...helpers import load_json
from ...helpers import save_json
from ...message import Channel
from ...message import IncomingJoin
from ...message import IncomingKick
from ...message import IncomingPart
from ...message import IncomingPrivateMessage
from ...message import IncomingQuit
from ...message import Message
from ...message import Nick
from ...message import Target
from ...signals import message_out
from ...signals import on_exception
from .. import Args
from .. import AuthContext
from .. import BaseModule
from .. import BaseResponder
from .. import CommandHandler
from .. import command
from .. import parse_command
from .. import predicates
from .. import privmsg_message_handler
from .. import reply_handler
from ..lib import Color
from ..lib import MemoryCache
from ..lib import colored
from .auth import AuthConfig
from .auth import AuthConfigPerson


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

    @reply_handler(Code.RPL_NAMREPLY)
    def handler_rpl_namreply(self, msg: Message) -> None:
        channel = Channel(msg.params[2])
        if channel not in self._current:
            self._current[channel] = []
        self._current[channel].extend([Nick(cleanup_nick(v)) for v in msg.params[3].split(' ')])

    @reply_handler(Code.RPL_ENDOFNAMES)
    def handler_rpl_endofnames(self, msg: Message) -> None:
        channel = Channel(msg.params[1])
        if channel not in self._current:
            return
        self._cache.set(channel, self._current.pop(channel))
        self._run_deferred()

    @join_message_handler()
    def handler_join(self, msg: IncomingJoin) -> None:
        nicks = self._cache.get(msg.channel)
        if nicks is not None and msg.nick not in nicks:
            nicks.append(msg.nick)

    @part_message_handler()
    def handler_part(self, msg: IncomingPart) -> None:
        nicks = self._cache.get(msg.channel)
        if nicks is not None and msg.nick in nicks:
            nicks.remove(msg.nick)

    @quit_message_handler()
    def handler_quit(self, msg: IncomingQuit) -> None:
        for (_, names) in self._cache:
            if msg.nick in names:
                names.remove(msg.nick)

    @kick_message_handler()
    def handler_kick(self, msg: IncomingKick) -> None:
        nicks = self._cache.get(msg.channel)
        if nicks is not None and msg.kickee in nicks:
            nicks.remove(msg.kickee)

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


def _is_authorised_has_uuid_and_sent_a_privmsg() -> Callable[[CommandHandler], CommandHandler]:
    def predicate(module: 'Vibecheck', msg: IncomingPrivateMessage, auth: AuthContext) -> bool:
        config = module.get_config()

        if config.authorised_group not in auth.groups:
            return False

        if not auth.uuid:
            return False

        if msg.target.is_channel:
            return False

        return True

    return predicates([predicate])


@dataclass()
class VibecheckConfig:
    data: str
    channel: str
    authorised_group: str

    def __post_init__(self) -> None:
        if self.data == '':
            raise ValueError('data cannot be empty')

        if self.channel == '':
            raise ValueError('channel cannot be empty')

        if self.authorised_group == '':
            raise ValueError('authorised_group cannot be empty')


class Vibecheck(NamesMixin, BaseResponder[VibecheckConfig]):
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
    config_class = VibecheckConfig

    store: Store
    maybe_pester_people_every = 60 * 15  # [s]

    def __init__(self, config: Config) -> None:
        super().__init__(config)
        self._store = Store(lambda: self.get_config().data)
        self._stop_event = threading.Event()
        self._t = threading.Thread(target=self._run)
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

            config = self.get_config()

            auth_module_people = self._peek_auth_module_people(config)
            auth_module_people_uuids = set([person.uuid for person in auth_module_people])

            with self._store as state:
                report = state.generate_report(self._now(), auth.uuid, names, auth_module_people_uuids)

            self.respond(
                msg,
                'Everyone currently in the channel: {}'.format(
                    ', '.join([v.for_display(auth.uuid) for v in reversed(report.persona_reports)])
                )
            )

            self.respond(msg, f'If you would like to endorse anyone then you can privately use the \'{command_prefix}endorse NICK\' command in this buffer. Please note that this isn\'t a big decision as you can easily reverse it with \'{command_prefix}unendorse NICK\'.')
            self.respond(msg, f'Transparency: {report.authorised_people_report.for_display()}')

        channel = Channel(self.get_config().channel)
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

        channel = Channel(self.get_config().channel)
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

        channel = Channel(self.get_config().channel)
        self.request_names(channel, on_names_available)

    @privmsg_message_handler()
    def handle_privmsg(self, msg: IncomingPrivateMessage) -> None:
        channel = msg.target.channel
        if channel is not None:
            if channel == Channel(self.get_config().channel):
                with self._store as state:
                    state.on_privmsg(msg.sender)

    def stop(self) -> None:
        super().stop()
        self._stop_event.set()
        self._t.join()

    def _run(self) -> None:
        while not self._stop_event.is_set():
            try:
                self._update()
                self._stop_event.wait(self.maybe_pester_people_every)
            except Exception as e:
                on_exception.send(self, e=e)

    def _now(self) -> datetime:
        return datetime.now()

    def _update(self) -> None:
        def on_names_available(names: list[Nick]) -> None:
            self._maybe_pester_people(names)
            self._mark_names_as_in_the_channel(names)

        channel = Channel(self.get_config().channel)
        self.request_names(channel, on_names_available)

    def _maybe_pester_people(self, names: list[Nick]) -> None:
        config = self.get_config()
        command_prefix = self.get_command_prefix()
        auth_module_people = self._peek_auth_module_people(config)
        auth_module_people_uuids = set([person.uuid for person in auth_module_people])
        for person in auth_module_people:
            with self._store as state:
                report = state.generate_pestering_report(self._now(), person.uuid, names, auth_module_people_uuids)
            if report is not None:
                for nick in [Target(Nick(nick_string)) for nick_string in person.contact]:
                    self.message(nick, 'Skybird, this is Dropkick with a red dash alpha message in two parts. Break. Break. Stand by to copy the list of people who are currently in the channel:')
                    self.message(nick, ', '.join([v.for_display(person.uuid) for v in reversed(report.persona_reports)]))
                    self.message(nick, f'If you would like to endorse any of them then you can privately use the \'{command_prefix}endorse NICK\' command in this buffer. Please note that this isn\'t a big decision as you can easily reverse it with \'{command_prefix}unendorse NICK\'. If you want to see the full report use the \'{command_prefix}vibecheck\' command.')

    def _mark_names_as_in_the_channel(self, names: list[Nick]) -> None:
        with self._store as state:
            state.mark_as_being_in_the_channel(names)

    def _peek_auth_module_people(self, config: VibecheckConfig) -> list[AuthConfigPerson]:
        auth_config = self.peek_loaded_config_for_module('botnet', 'auth', AuthConfig)
        return [
            person for person in auth_config.people
            if config.authorised_group in person.groups
        ]


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

    def on_join(self, nick: Nick) -> None:
        if nick not in self.nick_infos:
            self.nick_infos[nick] = NickInfo.new_due_to_being_in_the_channel()
            return
        self.nick_infos[nick].on_being_in_the_channel()

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

    def generate_report(self, now: datetime, auth_uuid: str, nicks: list[Nick], authorised_group_auth_uuids: set[str]) -> MinorityReport:
        self._mark_command_executed(auth_uuid)
        return MinorityReport.generate(now, self, nicks, authorised_group_auth_uuids)

    def generate_pestering_report(self, now: datetime, auth_uuid: str, nicks: list[Nick], authorised_group_auth_uuids: set[str]) -> MinorityReport | None:
        if auth_uuid in self.authorised_people_infos:
            if not self.authorised_people_infos[auth_uuid].should_pester():
                return None
        self._mark_pestered(auth_uuid)
        return MinorityReport.generate(now, self, nicks, authorised_group_auth_uuids)

    def mark_as_being_in_the_channel(self, nicks: list[Nick]) -> None:
        for nick in nicks:
            if nick not in self.nick_infos:
                self.nick_infos[nick] = NickInfo.new_due_to_being_in_the_channel()
                return
            self.nick_infos[nick].on_being_in_the_channel()

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
    first_join: None | datetime
    last_join: None | datetime
    first_seen_in_the_channel: None | datetime
    last_seen_in_the_channel: None | datetime
    endorsements: list[str]

    @classmethod
    def new_due_to_join(cls) -> NickInfo:
        now = datetime.now()
        return cls(
            first_message=None,
            last_message=None,
            first_join=now,
            last_join=now,
            first_seen_in_the_channel=now,
            last_seen_in_the_channel=now,
            endorsements=[],
        )

    @classmethod
    def new_due_to_being_in_the_channel(cls) -> NickInfo:
        now = datetime.now()
        return cls(
            first_message=None,
            last_message=None,
            first_join=None,
            last_join=None,
            first_seen_in_the_channel=now,
            last_seen_in_the_channel=now,
            endorsements=[],
        )

    @classmethod
    def new_due_to_privmsg(cls) -> NickInfo:
        now = datetime.now()
        return cls(
            first_message=now,
            last_message=now,
            first_join=None,
            last_join=None,
            first_seen_in_the_channel=now,
            last_seen_in_the_channel=now,
            endorsements=[],
        )

    @classmethod
    def new_due_to_endorsement(cls, endorser_uuid: str) -> NickInfo:
        return cls(
            first_message=None,
            last_message=None,
            first_join=None,
            last_join=None,
            first_seen_in_the_channel=None,
            last_seen_in_the_channel=None,
            endorsements=[endorser_uuid],
        )

    def on_join(self) -> None:
        now = datetime.now()

        if self.first_join is None:
            self.first_join = now
        self.last_join = now

        # update old entries
        if self.first_seen_in_the_channel is None:
            self.first_seen_in_the_channel = now
        if self.last_seen_in_the_channel is None:
            self.last_seen_in_the_channel = now

    def on_privmsg(self) -> None:
        now = datetime.now()

        if self.first_message is None:
            self.first_message = now
        self.last_message = now

        # update old entries
        if self.first_seen_in_the_channel is None:
            self.first_seen_in_the_channel = now
        if self.last_seen_in_the_channel is None:
            self.last_seen_in_the_channel = now

    def on_being_in_the_channel(self) -> None:
        now = datetime.now()

        # update old entries
        if self.first_seen_in_the_channel is None:
            self.first_seen_in_the_channel = now
        if self.last_seen_in_the_channel is None:
            self.last_seen_in_the_channel = now

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
    authorised_people_report: AuthorisedPeopleReport

    @classmethod
    def generate(cls, now: datetime, state: State, nicks: list[Nick], authorised_group_auth_uuids: set[str]) -> MinorityReport:
        authorised_people_report = AuthorisedPeopleReport.new(now, state, authorised_group_auth_uuids)
        report = cls([], authorised_people_report)

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
        if len(self.endorsements) == 0:
            warning_no_endorsements = colored('0', Color.RED)
        else:
            warning_no_endorsements = ''
        return '{} ({}{})'.format(nicks, '^' if endorsed else '?', warning_no_endorsements)


@dataclass
class AuthorisedPeopleReport:
    uuids: set[str]
    median_last_interaction_days: None | float
    max_last_interaction_days: None | float

    @classmethod
    def new(cls, now: datetime, state: State, authorised_people_uuids: set[str]) -> AuthorisedPeopleReport:
        last_interaction_days: list[float | None] = []

        for uuid in authorised_people_uuids:
            info = state.authorised_people_infos.get(uuid)
            if info is not None:
                if info.last_command_executed_at is not None:
                    delta = now - info.last_command_executed_at
                    if delta.days > 0:
                        last_interaction_days.append(delta.days)
                    else:
                        last_interaction_days.append(0)
                else:
                    last_interaction_days.append(None)

        if len(last_interaction_days) > 0:
            sorted_data = sorted(last_interaction_days, key=lambda x: (x is None, x))
            max_last_interaction_days = sorted_data[-1]
            median_last_interaction_days = sorted_data[(len(sorted_data) - 1) // 2]
        else:
            median_last_interaction_days = None
            max_last_interaction_days = None

        return AuthorisedPeopleReport(authorised_people_uuids, median_last_interaction_days, max_last_interaction_days)

    def for_display(self) -> str:
        sorted_uuids = sorted(list(self.uuids))
        if self.median_last_interaction_days is None:
            age_median = colored('never (!)', Color.RED)
        else:
            if self.median_last_interaction_days < 30:
                age_median = colored(f'in the last {self.median_last_interaction_days} days', Color.GREEN)
            else:
                age_median = colored(f'in the last {self.median_last_interaction_days} days', Color.RED)

        if self.max_last_interaction_days is None:
            age_max = colored('never (!)', Color.RED)
        else:
            if self.max_last_interaction_days < 30:
                age_max = colored(f'in the last {self.max_last_interaction_days} days', Color.GREEN)
            else:
                age_max = colored(f'in the last {self.max_last_interaction_days} days', Color.RED)

        return 'authorised group consists of {}; median last age of interaction with this module is {}, max last age of interaction with this module is {}.'.format(
            ', '.join(sorted_uuids),
            age_median,
            age_max,
        )


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
    first_join: None | float
    last_join: None | float
    first_seen_in_the_channel: None | float
    last_seen_in_the_channel: None | float
    endorsements: list[str]

    @classmethod
    def create(cls, v: NickInfo) -> TransportNickInfo:
        return cls(
            v.first_message.timestamp() if v.first_message is not None else None,
            v.last_message.timestamp() if v.last_message is not None else None,
            v.first_join.timestamp() if v.first_join is not None else None,
            v.last_join.timestamp() if v.last_join is not None else None,
            v.first_seen_in_the_channel.timestamp() if v.first_seen_in_the_channel is not None else None,
            v.last_seen_in_the_channel.timestamp() if v.last_seen_in_the_channel is not None else None,
            v.endorsements,
        )

    def to(self) -> NickInfo:
        return NickInfo(
            datetime.fromtimestamp(self.first_message) if self.first_message is not None else None,
            datetime.fromtimestamp(self.last_message) if self.last_message is not None else None,
            datetime.fromtimestamp(self.first_join) if self.first_join is not None else None,
            datetime.fromtimestamp(self.last_join) if self.last_join is not None else None,
            datetime.fromtimestamp(self.first_seen_in_the_channel) if self.first_seen_in_the_channel is not None else None,
            datetime.fromtimestamp(self.last_seen_in_the_channel) if self.last_seen_in_the_channel is not None else None,
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

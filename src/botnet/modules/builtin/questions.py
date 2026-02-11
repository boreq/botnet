from dataclasses import dataclass
from typing import Callable

from ...message import Channel
from ...message import IncomingPrivateMessage
from .. import AuthContext
from .. import BaseResponder
from .. import CommandHandler
from .. import command
from .. import predicates


@dataclass()
class ChannelQuestions:
    channel: str
    questions: list[str]

    def __post_init__(self) -> None:
        if len(self.questions) == 0:
            raise ValueError('questions are empty')


@dataclass()
class QuestionsConfig:
    channel_questions: list[ChannelQuestions]


def _sent_in_channel_and_there_are_questions_for_this_channel() -> Callable[[CommandHandler], CommandHandler]:
    def predicate(module: 'Questions', msg: IncomingPrivateMessage, auth: AuthContext) -> bool:
        config = module.get_config()
        channel = msg.target.channel
        if channel is not None:
            for v in config.channel_questions:
                if Channel(v.channel) == channel and len(v.questions) > 0:
                    return True
        return False
    return predicates([predicate])


class Questions(BaseResponder[QuestionsConfig]):
    """Questions lets you specify a list of question to ask people in the channel.

    Example module config:

        "botnet": {
            "questions": {
                "channel_questions": [
                    {
                        "channel": "#channel",
                        "questions": [
                            "What is your name?",
                            "Where are you from?"
                        ]
                    }
                ]
            }
        }

    """

    config_namespace = 'botnet'
    config_name = 'questions'
    config_class = QuestionsConfig

    @command('questions')
    @_sent_in_channel_and_there_are_questions_for_this_channel()
    def command_questions(self, msg: IncomingPrivateMessage, auth: AuthContext) -> None:
        """Replies with the list of questions for the channel.

        Syntax: questions
        """
        channel = msg.target.channel
        if channel is not None:
            config = self.get_config()
            for v in config.channel_questions:
                if Channel(v.channel) == channel:
                    for (i, question) in enumerate(v.questions):
                        message = f'{i}. {question}'
                        self.respond(msg, message)


mod = Questions

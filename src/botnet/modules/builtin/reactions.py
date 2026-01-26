from dataclasses import dataclass
import random
from .. import BaseResponder, command, AuthContext, parse_command, Args
from ...message import IncomingPrivateMessage


cutelist = [
    '✿◕ ‿ ◕✿',
    '❀◕ ‿ ◕❀',
    '(✿◠‿◠)',
    '(◕‿◕✿) ',
    '( ｡◕‿◕｡)',
    '(◡‿◡✿)',
    '⊂◉‿◉つ ❤',
    '{{ ◕ ◡ ◕}}',
    '( ´・‿-) ~ ♥',
    '(っ⌒‿⌒)っ~ ♥',
    'ʕ´•ᴥ•`ʔσ”',
    '(･Θ･) caw',
    '(=^･ω･^)y＝',
    'ヽ(=^･ω･^=)丿',
    '~(=^･ω･^)ヾ(^^ )',
    '| (•□•) | (❍ᴥ❍ʋ)',
    'ϞϞ(๑⚈ ․̫ ⚈๑)∩',
    'ヾ(･ω･*)ﾉ',
    '▽・ω・▽ woof~',
    '(◎｀・ω・´)人(´・ω・｀*)',
    '(*´・ω・)ノ(-ω-｀*)',
    '(❁´ω`❁)',
    '(＊◕ᴗ◕＊)',
    '{{´◕ ◡ ◕｀}}',
    '₍•͈ᴗ•͈₎',
    '(˘･ᴗ･˘)',
    '(ɔ ˘⌣˘)˘⌣˘ c)',
    '(⊃｡•́‿•̀｡)⊃',
    '(´ε｀ )♡',
    '(◦˘ З(◦’ںˉ◦)♡',
    '( ＾◡＾)っ~ ❤ Leper',
    '╰(　´◔　ω　◔ `)╯',
    '(*･ω･)',
    '(∗•ω•∗)',
    '( ◐ω◐ )',
]

cutelist_target = [
    '(✿◠‿◠)っ~ ♥ {target}',
    '⊂◉‿◉つ ❤ {target}',
    '( ´・‿-) ~ ♥ {target}',
    '(っ⌒‿⌒)っ~ ♥ {target}',
    'ʕ´•ᴥ•`ʔσ” BEARHUG {target}',
    '(⊃｡•́‿•̀｡)⊃ U GONNA GET HUGGED {target}',
    '( ＾◡＾)っ~ ❤ {target}',
    '{target} (´ε｀ )♡',
    '{sender} ~(=^･ω･^)ヾ(^^ ) {target}',
    '{sender} (◎｀・ω･´)人(´・ω・｀*) {target}',
    '{sender} (*´・ω・)ノ(-ω-｀*) {target}',
    '{sender} (ɔ ˘⌣˘)˘⌣˘ c) {target}',
    '{sender} (◦˘ З(◦’ںˉ◦)♡ {target}',
]


magiclist = [
    '(つ˵•́ω•̀˵)つ━☆ﾟ.*･｡ﾟ҉̛ {target}',
    '(つ˵•́ω•̀˵)つ━☆✿✿✿✿✿✿ {target}',
    '╰( ´・ω・)つ──☆ﾟ.*･｡ﾟ҉̛ {target}',
    '╰( ´・ω・)つ──☆✿✿✿✿✿✿ {target}',
    '(○´･∀･)o<･。:*ﾟ;+． {target}',
]


@dataclass()
class ReactionsConfig:
    pass


class Reactions(BaseResponder[ReactionsConfig]):
    """Defines several commands related to emotional reactions."""

    config_namespace = 'botnet'
    config_name = 'reactions'
    config_class = ReactionsConfig

    @command('cute')
    @parse_command([('nicks', '*')])
    def command_cute(self, msg: IncomingPrivateMessage, auth: AuthContext, args: Args) -> None:
        """Sends a random emoticon. The style of an emoticon changes if the
        TARGET is defined.

        Syntax: cute [NICK ...]
        """
        nicks = args['nicks']
        if len(nicks) > 0:
            self.send_from_list(msg, nicks, cutelist_target)
        else:
            self.send_from_list(msg, nicks, cutelist)

    @command('magic')
    @parse_command([('nicks', '*')])
    def command_magic(self, msg: IncomingPrivateMessage, auth: AuthContext, args: Args) -> None:
        """Sends a random emoticon.

        Syntax: magic [NICK ...]
        """
        nicks = args['nicks']
        self.send_from_list(msg, nicks, magiclist)

    def send_from_list(self, msg: IncomingPrivateMessage, nicks: list[str], reactions_list: list[str]) -> None:
        target = ' '.join(nicks)
        response = random.choice(reactions_list).format(sender=msg.sender,
                                                        target=target)
        self.respond(msg, response)


mod = Reactions

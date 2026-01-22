import random
from .. import BaseResponder, command, AuthContext
from ..lib import parse_command, Args
from ...message import Message


cutelist = [
    '✿◕ ‿ ◕✿',
    '❀◕ ‿ ◕❀',
    '(✿◠‿◠)',
    '(◕‿◕✿) ',
    '( ｡◕‿◕｡)',
    '(◡‿◡✿)',
    '⊂◉‿◉つ ❤',
    '{ ◕ ◡ ◕}',
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
    '{´◕ ◡ ◕｀}',
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
    '{sender} (◎｀・ω・´)人(´・ω・｀*) {target}',
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


class Reactions(BaseResponder):
    """Defines several commands related to emotional reactions."""

    @command('cute')
    @parse_command([('target', '*')])
    def command_cute(self, msg: Message, auth: AuthContext, args: Args) -> None:
        """Sends a random emoticon. The style of an emoticon changes if the
        TARGET is defined.

        Syntax: cute [TARGET ...]
        """
        if len(args.target) > 0:
            self.send_from_list(msg, args, cutelist_target)
        else:
            self.send_from_list(msg, args, cutelist)

    @command('magic')
    @parse_command([('target', '*')])
    def command_magic(self, msg: Message, auth: AuthContext, args: Args) -> None:
        """Sends a random emoticon.

        Syntax: magic [TARGET ...]
        """
        self.send_from_list(msg, args, magiclist)

    def send_from_list(self, msg: Message, args: Args, reactions_list: list[str]) -> None:
        target = ' '.join(args.target)
        response = random.choice(reactions_list).format(sender=msg.nickname,
                                                        target=target)
        self.respond(msg, response)


mod = Reactions

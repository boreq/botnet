from . import BaseResponder, parse_command
from ..message import Message
from ..signals import module_loaded, module_unloaded, module_load, \
    module_unload, message_out


class Control(BaseResponder):
    """Adds command which allow to control the bot.

    Example config:

        "control": {
            "admins": ["nickname"]
        },

    """

    def __init__(self, config):
        super(Control, self).__init__(config)
        self.config = config.get_for_module('control')
        module_loaded.connect(self.on_module_loaded)
        module_unloaded.connect(self.on_module_unloaded)

    def tell_admins(self, text):
        """Sends a message to all admins defined in the config."""
        for nickname in self.config['admins']:
            msg = Message(command='PRIVMSG', params=[nickname, text])
            message_out.send(self, msg=msg)

    def on_module_loaded(self, sender, cls):
        """Handler for on_module_loaded signal. Informs all admins about the
        event.
        """
        self.tell_admins('Module loaded %s' % cls)

    def on_module_unloaded(self, sender, cls):
        """Handler for on_module_unloaded signal. Informs all admins about the
        event.
        """
        self.tell_admins('Module unloaded %s' % cls)

    @parse_command([('modules', '+')], launch_invalid=False)
    def command_load(self, msg, args):
        """Loads a module.

        load MODULE_NAME ...
        """
        if not msg.nickname in self.config['admins']:
            return
        for name in args.modules:
            module_load.send(self, name=name)

    @parse_command([('modules', '+')], launch_invalid=False)
    def command_unload(self, msg, args):
        """Unloads a module.

        unload MODULE_NAME ...
        """
        if not msg.nickname in self.config['admins']:
            return
        for name in args.modules:
            module_unload.send(self, name=name)


mod = Control

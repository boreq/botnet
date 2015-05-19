# Writing external modules
Botnet supports external modules loaded from other Python packages installed
separately from the main Botnet package.

## Basics
A Botnet module is a class which inherits from `botnet.modules.BaseModule`.
Botnet modules communicate using signals defined in `botnet.signals`. For
example to create the most basic module you could write a class similar to the
one shown below to handle incoming and outgoing messages:

    from botnet import Message, BaseModule, message_in, message_out

    class MyModule(BaseModule):

        def __init__(self, config):
            super(MyModule, self).__init__(config)
            message_in.connect(self.on_message_in)

        def on_message_in(self, msg):
            """Responds with a text each time a message is received."""
            target = msg.params[0]
            text = 'I got a message!'
            response = Message(command='PRIVMSG', params=[target, text])
            message_out.send(self, msg=response)


That however requires knowledge about internal implementation of this bot and
about the IRC protocol (even the code above contains a bug - for simplicity it
can't handle private messages). That is why it is much easier and recommended
to use the already written `BaseModule` subclasses.

## Subclassing
The most versatile class to subclass is `botnet.modules.BaseResponder`.
It automatically dispatches incoming messages to the appropriate handlers and
provides an easy way to respond to them.

    from botnet import BaseResponder

    class MyModule(BaseResponder):

        def handle_privmsg(self, msg):
            """Responds with a text each time a message is received."""
            self.respond(msg, 'I got a message!')


The `examples` directory contains examples which show how to implement commands
using separate methods and go through some more advanced features of that class,
hopefully they will be enough to get you going.

## Distributing external modules
There are two conditions to distributing external Botnet modules in a separate
Python package:

1. The Python package name must start with `botnet_`.
   This is required to differentiate between built-in and external Botnet
   modules in the config file.
2. If a user writes `botnet_custom.my_module` in the config file, Botnet will
   try to execute the equivalent of the following statement:
   `from botnet_custom.my_module import mod`. As you can see inside a file
   containing the module class there should be a variable `mod` pointing to it.
   Thanks to that it is possible to avoid writing a possibly long import
   statement in the Python package and updating it every time you want to add
   a new module (it can also simply be an insane and annoying requirement
   forcing you to write the package in the certain way, depending on your point
   of view).

An example of a Python package containing several external modules can be found
here: <https://github.com/boreq/botnet_modules>.

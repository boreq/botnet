# Botnet
IRC bot written in Python.

Botnet implements nearly all core functionality in a form of modules which can
be loaded and unloaded at will and communicate with one another using signals.
Thanks to that design a module which encounters serious issues and crashes is
automatically restarted and does not affect the execution of other modules.
Furthermore all features of the bot can be enabled and disabled at will. It is
possible to use built-in modules or create easy to load and integrate user
maintained external modules distributed in a form of Python packages.

## Usage

    botnet --help
    botnet run --help
    botnet run /path/to/config.json

## Example config

    {
        "modules": ["irc", "meta"],
        "module_config": {
            "botnet": {
                "irc": {
                    "server": "irc.example.com",
                    "port": 6697,
                    "ssl": true,
                    "nick": "my_bot",
                    "channels": [
                        {
                            "name": "#my-channel",
                            "password": null
                        }
                    ],
                    "autosend": [
                        "PRIVMSG your_nick :I connected!"
                    ]
                },
                "base_responder": {
                    "command_prefix": "."
                }
            }
        }
    }

# Botnet
IRC bot written in Python.

## Usage

    botnet --help
    botnet run --help
    botnet run /path/to/config.json

## Example config

    {
        "modules": ["irc", "meta"],
        "module_config": {
            "irc": {
                "server": "irc.example.com",
                "port": 6667,
                "ssl": false,
                "nick": "my_bot",
                "channels": [
                    {
                        "name": "#my-channel",
                        "password": null
                    }
                ]
            },
            "base_responder": {
                "command_prefix": "."
            }
        }
    }

## Creating external modules
The easiest way to create a module is to subclass
`botnet.modules.BaseResponder`. For details see a simple built-in module
`botnet.modules.meta`.

External modules must follow a few simple rules:

* Python module name should start with `botnet_`
* is should be possible to import a variable `mod` from that Python module
* variable `mod` should be pointing to a class which is a child of
`botnet.modules.BaseIdleModule`
* if a module requires additional configuration it should be stored in
`module_config->external_module_name`

To load an external module it is necessary it to install and add it to
`modules` in the config file. Example:


    {
        "modules": ["irc", "botnet_cool_external_module"],
        "module_config": {
            "botnet_cool_external_module": {
                "key": "value"
            }
            ...
        }
    }

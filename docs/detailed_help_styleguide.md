# Detailed help styleguide
This guide should be followed when writing a response to the detailed help
command (`.help command_name`). For the `BaseResponder` this is simply a
docstring of a method which implements the particular command.

## General format
This format should be followed when adding the detailed help for commands in the
source code of a module, for example in docstrings.

    <description>

    Syntax: <syntax>

### Description
A description should explain the result of running the command in a concise
manner.

### Syntax
A syntax string presents an exact syntax of a command.

A syntax string should:
* start with the command name
* contain command arguments in UPPERCASE
* contain optional arguments in [BRACKETS]
* indicate a possibility of using further identical arguments with three
  dots `...` placed after a command argument and separated from it with
  a space

Examples:

    # no arguments
    command_name

    # one required argument
    command_name ARGUMENT_NAME

    # first required argument must appear only once, the second at least once
    command_name REQUIRED_ARGUMENT1 REQUIRED_ARGUMENT2 ...

    # first argument is required, the second one optional
    command_name REQUIRED_ARGUMENT [OPTIONAL_ARGUMENT]

    # first argument is required, the second one optional and can appear multiple times
    command_name REQUIRED_ARGUMENT [OPTIONAL_ARGUMENT ...]


## Sending the detailed help
If you intend to implement the `help` command yourself try to follow those
guidelines while sending the detailed help message.

A general format of a response:

    Module <module_name>, help for <command_name>: <detailed_help>

### Module name
Module name can be the name of the Botnet module, the name of the class which
implements a Botnet module, a string which is placed in the config to load the
module etc. A module name should make it easy to identify the origin of a
command.

### Command name
An exact name of the command.

### Detailed help
The detailed help message should be reformatted in the following way:
* multiple lines should be joined with spaces
* multiple spaces used in a row should be replaced with a single space
* the response should fit in one message

For example:

    Lorem.
    Ipsum.

    Syntax: command ARG

should turn into:

    Lorem. Ipsum. Syntax: command ARG

### Example
    Module SimpleModule, help for respond: Sends a message 'Responding!'. Syntax: respond

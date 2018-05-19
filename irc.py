import socket
import sys
import ssl
import time
import random
import itertools
import json
import threading
from commands import get_command


if len(sys.argv) < 2:
    print("Usage: irc.py [config.json]")
    exit(1)
#load config from json, check if everything is alright
with open(sys.argv[1], 'r') as data_file:
    try:
        config = json.loads(data_file.read())
    except ValueError:
        print('Please provide valid config')
        exit(1)
try:
    server = config["server"]
    port = config["port"]
    channel_list = config["channels"]
    if config["bot_nick"]:
        botnick = config["bot_nick"]
    else:
        botnick = "BOT" + str(random.randint(1, 9999))
    password = config["password"]
    commandprefix = config["prefix"]
except KeyError:
    print('Please provide valid config')
    exit(1)

def sendmsg(recipient, msg):
    """Sends a message."""
    with lock:
        if msg and isinstance(msg, tuple):
            for i in msg:
                ircsock.send("PRIVMSG %s :%s\n" % (recipient, i))
        elif msg:
            ircsock.send(bytes("PRIVMSG %s :%s\n" % (recipient, msg), 'UTF-8'))

def joinchan(chan):
    """Joins a channel."""
    with lock:
        print("trying")
        ircsock.send(bytes("JOIN %s\n" % chan, 'UTF-8'))

def auth(pass_word):
    """Works only on Nickserv servers"""
    sendmsg("Nickserv", "identify %s" % pass_word)

def parsemsg(s):
    """Breaks a message from an IRC server into its prefix, command, and
    arguments.
    """

    # TODO: Refactor the fuck out of this
    prefix = ""
    trailing = []
    retargs = []
    raw = s
    command = ""
    if not s:
        pass
    if s[0] == ":":
        prefix, s = s[1:].split(" ", 1)
    if s.find(" :") != -1:
        s, trailing = s.split(" :", 1)
        args = s.split()
        args.append(trailing)
        if trailing[0] == commandprefix:
            commands = args[2][1:].strip().split() if len(args) >= 3 else ""
            if commands:
                command = commands[0]
                retargs = commands[1:]
        else:
            pass
    else:
        args = s.split()
    event = args[0]
    channel = args[1]

    # If there is nothing in command at this point
    # We append whatever is in event as a command.
    # Easier to handle events like ping
    command = event if not command else command
    ret = {"prefix": prefix,
           "command": command,
           "raw": raw,
           "event": event,
           "args": retargs,
           "channel": channel,

        # Because circular imports
           "sendmsg": sendmsg}
    return ret


_partial_data = None


def process_data(data):
    """Process the data received from the socket. Ensures that there is no
    partial command at the end of the data chunk (that can happen if the data
    does not fit in the socket buffer). If that happens the partial command will
    be reconstructed next time this function is called.

    data: raw data from the socket.
    """
    global _partial_data
    try:
        data = data.decode(encoding='UTF-8')
    except Exception as e:
        return
    if not data:
        return []
    lines = data.splitlines()
    # There is at least one newline => this data chunk contains the end of at
    # least one command. If previous command was stored then it is complete now.
    if "\n" in data and _partial_data:
        lines[0] = _partial_data + lines[0]
        _partial_data = None
    # Store partial data.
    if not data.endswith("\n"):
        if _partial_data is None:
            _partial_data = ""
        _partial_data += lines.pop()
    return lines

def isplit(iterable,splitters):
    return [list(g) for k,g in itertools.groupby(iterable,lambda x:x in splitters) if not k]

def pipe_commands(args, channel):
    pipelist = args["args"].copy()
    pipelist.insert(0,args["command"])
    l = isplit(pipelist,"|")
    out = None
    for i in l:
        cmd = i[0].strip(".")
        a = i[1:]
        if out:
            a.append(out)
        args["command"] = cmd
        args["args"] = a
        print(a)
        c = get_command(args["command"])
        print(type(c), c)
        if not cmd == "rate" or not cmd == "r8":
            out = "".join(c(args))
    sendmsg(channel, out)



s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
lock = threading.Lock()
time.sleep(.5)
s.connect((server, port))
time.sleep(.5)
ircsock = ssl.wrap_socket(s)
time.sleep(.5)
ircsock.send(bytes("USER %s %s %s :some stuff\n" % (botnick, botnick, botnick), 'UTF-8'))
time.sleep(.5)
ircsock.send(bytes("NICK %s\n" % botnick, 'UTF-8'))
if password:
    time.sleep(.5)
    auth(password)
time.sleep(.5)
for channel in channel_list:
    joinchan(channel)
    time.sleep(.5)

while True:
    data = ircsock.recv(1024)
    try:
        valid_data = process_data(data)
    except Exception as e:
        continue
    if not valid_data:
        continue
    print(data)
    for ircmsg in process_data(data):
        if "PING :" in ircmsg:
            with lock:
                ircsock.send(bytes("PONG :ping\n", 'UTF-8'))
        elif "/QUOTE PONG" in ircmsg:
            confirm = "PONG " + ircmsg.split()[-1:][0] + "\r\n"
            with lock:
                ircsock.send(bytes(confirm, 'UTF-8'))
            for channel in channel_list:
                joinchan(channel)
                time.sleep(.5)
        elif any(channel in ircmsg for channel in channel_list):
            try:
                args = parsemsg(str(ircmsg))
                args['config'] = config

                channel = args['channel']
                if "|" in args["args"]:
                    pipe_commands(args, channel)
                else:
                    cmd = get_command(args["command"])
                    try:
                        sendmsg(channel, cmd(args))
                    except Exception as e:
                        print(e)
                        sendmsg(channel, (str(e)))
            except Exception as e:
                pass

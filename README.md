cybot
=====

*an IRC bot written in something that may resemble python*


__Features include:__
* featured in quality channels IRC-wide
* the subject of much debate and controversy
* runs on __any hardware__ (that runs python 3.4)
* fresh, new talent in the bot world

__Reviews:__
 * *Futanarcharist* __│__ best bot evar
 * *Leper* __│__ p. good, 8/10, would fork again
 * *b0tn3t* __│__ ok bub
 *  newuser │ cybits threatened the president with death



For extensive help, all you have to do is type `.cybhelp` in the channel! Guaranteed to be 100% helpful.

For any nerds not running a good shell, to get the bot running:

```
cd cybot
pip install -r requirements.txt
python irc.py <config.json>
```

Config Syntax
```
{
    "server" : "irc.rizon.net", # server address
    "port" : 6697, # server port
    "bot_nick" : "cybot", # nick of bot, 0 for random nick
    "channels" : ["#bots", "#test"], # list of channels to connect to
    "password" : "bot123", # password of bot, 0 for no password
    "prefix" : "." # command prefix so commands start with $prefix
}
```

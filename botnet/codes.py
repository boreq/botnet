from enum import Enum, unique


@unique
class Code(Enum):
    """Enum with all numeric replies defined in RFC 2812. Also contains
    additional replies used by popular networks included at the bottom.
    """

    # Welcome to the Internet Relay Network <nick>!<user>@<host>
    RPL_WELCOME = 1

    # Your host is <servername>, running version <ver>
    RPL_YOURHOST = 2

    # This server was created <date>
    RPL_CREATED = 3

    # <servername> <version> <available user modes> <available channel modes>
    RPL_MYINFO = 4

    # Try server <server name>, port <port number>
    RPL_BOUNCE = 5

    # :*1<reply> *( " " <reply> )
    RPL_USERHOST = 302

    # :*1<nick> *(  " <nick> )"
    RPL_ISON = 303

    # "<nick> :<away message>"
    RPL_AWAY = 301

    # :You are no longer marked as being away
    RPL_UNAWAY = 305

    # :You have been marked as being away
    RPL_NOWAWAY = 306

    # <nick> <user> <host> * :<real name>
    RPL_WHOISUSER = 311

    # <nick> <server> :<server info>
    RPL_WHOISSERVER = 312

    # <nick> :is an IRC operator
    RPL_WHOISOPERATOR = 313

    # <nick> <integer> :seconds idle
    RPL_WHOISIDLE = 317

    # <nick> :End of WHOIS list
    RPL_ENDOFWHOIS = 318

    # <nick> :*( ( "@" / "+" ) <channel> " " )
    RPL_WHOISCHANNELS  = 319

    # <nick> <user> <host> * :<real name>
    RPL_WHOWASUSER = 314

    # <nick> :End of WHOWAS
    RPL_ENDOFWHOWAS  = 369

    # Obsolete. Not used.
    RPL_LISTSTART = 321

    # <channel> <# visible> :<topic>
    RPL_LIST =  322

    # :End of LIST
    RPL_LISTEND = 323

    # <channel> <nickname>
    RPL_UNIQOPIS = 325

    # <channel> <mode> <mode params>
    RPL_CHANNELMODEIS  = 324

    # <channel> :No topic is set
    RPL_NOTOPIC = 331

    # <channel> :<topic>
    RPL_TOPIC = 332

    # <channel> <nick>
    RPL_INVITING = 341

    # <user> :Summoning user to IRC
    RPL_SUMMONING = 342

    # <channel> <invitemask>
    RPL_INVITELIST = 346

    # <channel> :End of channel invite list
    RPL_ENDOFINVITELIST = 347

    # <channel> <exceptionmask>
    RPL_EXCEPTLIST = 348

    # <channel> :End of channel exception list
    RPL_ENDOFEXCEPTLIST = 349

    # <version>.<debuglevel> <server> :<comments>
    RPL_VERSION = 351

    #"<channel> <user> <host> <server> <nick>
    #( "H" / "G" > ["*"] [ ( "@" / "+" ) ]
    #:<hopcount> <real name>"
    RPL_WHOREPLY = 352

    # <name> :End of WHO list
    RPL_ENDOFWHO = 315

    # "( "=" / "*" / "@" ) <channel>
    # :[ "@" / "+" ] <nick> *( " " [ "@" / "+" ] <nick> )
    # - "@" is used for secret channels, "*" for private
    # channels, and "=" for others (public channels).
    RPL_NAMREPLY = 353

    # <channel> :End of NAMES list
    RPL_ENDOFNAMES = 366

    # <mask> <server> :<hopcount> <server info>
    RPL_LINKS = 364

    # <mask> :End of LINKS list
    RPL_ENDOFLINKS = 365

    # <channel> <banmask>
    RPL_BANLIST = 367

    # <channel> :End of channel ban list
    RPL_ENDOFBANLIST = 368

    # :<string>
    RPL_INFO = 371

    # :End of INFO list
    RPL_ENDOFINFO = 374

    # :- <server> Message of the day -
    RPL_MOTDSTART = 375

    # :- <text>
    RPL_MOTD = 372

    # :End of MOTD command
    RPL_ENDOFMOTD = 376

    # :You are now an IRC operator
    RPL_YOUREOPER = 381

    # <config file> :Rehashing
    RPL_REHASHING = 382

    # You are service <servicename>
    RPL_YOURESERVICE = 383

    # <server> :<string showing server's local time>
    RPL_TIME = 391

    # :UserID   Terminal  Host
    RPL_USERSSTART = 392

    # :<username> <ttyline> <hostname>
    RPL_USERS = 393

    # :End of users
    RPL_ENDOFUSERS = 394

    # :Nobody logged in
    RPL_NOUSERS = 395

    # Link <version & debug level> <destination>
    # <next server> V<protocol version>
    # <link uptime in seconds> <backstream sendq>
    # <upstream sendq>
    RPL_TRACELINK = 200

    # Try. <class> <server>
    RPL_TRACECONNECTING = 201

    # H.S. <class> <server>
    RPL_TRACEHANDSHAKE = 202

    # ???? <class> [<client IP address in dot form>]
    RPL_TRACEUNKNOWN = 203

    # Oper <class> <nick>
    RPL_TRACEOPERATOR = 204

    # User <class> <nick>
    RPL_TRACEUSER = 205

    # Serv <class> <int>S <int>C <server>
    # <nick!user|*!*>@<host|server> V<protocol version>
    RPL_TRACESERVER = 206

    # Service <class> <name> <type> <active type>
    RPL_TRACESERVICE = 207

    # <newtype> 0 <client name>
    RPL_TRACENEWTYPE = 208

    # Class <class> <count>
    RPL_TRACECLASS = 209

    # Unused.
    RPL_TRACERECONNECT = 210

    # File <logfile> <debug level>
    RPL_TRACELOG = 261

    # <server name> <version & debug level> :End of TRACE
    RPL_TRACEEND = 262

    # <linkname> <sendq> <sent messages>
    # <sent Kbytes> <received messages>
    # <received Kbytes> <time open>
    RPL_STATSLINKINFO = 211

    # <command> <count> <byte count> <remote count>
    RPL_STATSCOMMANDS = 212

    # <stats letter> :End of STATS report
    RPL_ENDOFSTATS = 219

    # :Server Up %d days %d:%02d:%02d
    RPL_STATSUPTIME = 242

    # O <hostmask> * <name>
    RPL_STATSOLINE = 243

    # <user mode string>
    RPL_UMODEIS = 221

    # <name> <server> <mask> <type> <hopcount> <info>
    RPL_SERVLIST = 234

    # <mask> <type> :End of service listing
    RPL_SERVLISTEND = 235

    # :There are <integer> users and <integer>
    # services on <integer> servers
    RPL_LUSERCLIENT = 251

    # <integer> :operator(s) online
    RPL_LUSEROP = 252

    # <integer> :unknown connection(s)
    RPL_LUSERUNKNOWN = 253

    # <integer> :channels formed
    RPL_LUSERCHANNELS = 254

    # :I have <integer> clients and <integer>
    #  servers
    RPL_LUSERME = 255

    # <server> :Administrative info
    RPL_ADMINME = 256

    # :<admin info>
    RPL_ADMINLOC1 = 257

    # :<admin info>
    RPL_ADMINLOC2 = 258

    # :<admin info>
    RPL_ADMINEMAIL = 259

    # <command> :Please wait a while and try again.
    RPL_TRYAGAIN = 263

    # <nickname> :No such nick/channel
    ERR_NOSUCHNICK = 401

    # <server name> :No such server
    ERR_NOSUCHSERVER = 402

    # <channel name> :No such channel
    ERR_NOSUCHCHANNEL = 403

    # <channel name> :Cannot send to channel
    ERR_CANNOTSENDTOCHAN = 404

    # <channel name> :You have joined too many channels
    ERR_TOOMANYCHANNELS = 405

    # <nickname> :There was no such nickname
    ERR_WASNOSUCHNICK = 406

    # <target> :<error code> recipients. <abort message>
    ERR_TOOMANYTARGETS = 407

    # <service name> :No such service
    ERR_NOSUCHSERVICE = 408

    # :No origin specified
    ERR_NOORIGIN = 409

    # :No recipient given (<command>)
    ERR_NORECIPIENT = 411

    # :No text to send
    ERR_NOTEXTTOSEND = 412

    # <mask> :No toplevel domain specified
    ERR_NOTOPLEVEL = 413

    # <mask> :Wildcard in toplevel domain
    ERR_WILDTOPLEVEL = 414

    # <mask> :Bad Server/host mask
    ERR_BADMASK = 415

    # <command> :Unknown command
    ERR_UNKNOWNCOMMAND = 421

    # :MOTD File is missing
    ERR_NOMOTD = 422

    # <server> :No administrative info available
    ERR_NOADMININFO = 423

    # :File error doing <file op> on <file>
    ERR_FILEERROR = 424

    # :No nickname given
    ERR_NONICKNAMEGIVEN = 431

    # <nick> :Erroneous nickname
    ERR_ERRONEUSNICKNAME = 432

    # <nick> :Nickname is already in use
    ERR_NICKNAMEINUSE = 433

    # <nick> :Nickname collision KILL from <user>@<host>
    ERR_NICKCOLLISION = 436

    # <nick/channel> :Nick/channel is temporarily unavailable
    ERR_UNAVAILRESOURCE = 437

    # <nick> <channel> :They aren't on that channel
    ERR_USERNOTINCHANNEL = 441

    # <channel> :You're not on that channel
    ERR_NOTONCHANNEL = 442

    # <user> <channel> :is already on channel
    ERR_USERONCHANNEL = 443

    # <user> :User not logged in
    ERR_NOLOGIN = 444

    # :SUMMON has been disabled
    ERR_SUMMONDISABLED = 445

    # :USERS has been disabled
    ERR_USERSDISABLED = 446

    # :You have not registered
    ERR_NOTREGISTERED = 451

    # <command> :Not enough parameters
    ERR_NEEDMOREPARAMS = 461

    # :Unauthorized command (already registered)
    ERR_ALREADYREGISTRED = 462

    # :Your host isn't among the privileged
    ERR_NOPERMFORHOST = 463

    # :Password incorrect
    ERR_PASSWDMISMATCH = 464

    # :You are banned from this server
    ERR_YOUREBANNEDCREEP = 465

    ERR_YOUWILLBEBANNED = 466

    # <channel> :Channel key already set
    ERR_KEYSET = 467

    # <channel> :Cannot join channel (+l)
    ERR_CHANNELISFULL = 471

    # <char> :is unknown mode char to me for <channel>
    ERR_UNKNOWNMODE = 472

    # <channel> :Cannot join channel (+i)
    ERR_INVITEONLYCHAN = 473

    # <channel> :Cannot join channel (+b)
    ERR_BANNEDFROMCHAN = 474

    # <channel> :Cannot join channel (+k)
    ERR_BADCHANNELKEY = 475

    # <channel> :Bad Channel Mask
    ERR_BADCHANMASK = 476

    # <channel> :Channel doesn't support modes
    ERR_NOCHANMODES = 477

    # <channel> <char> :Channel list is full
    ERR_BANLISTFULL = 478

    # :Permission Denied- You're not an IRC operator
    ERR_NOPRIVILEGES = 481

    # <channel> :You're not channel operator
    ERR_CHANOPRIVSNEEDED = 482

    # :You can't kill a server!
    ERR_CANTKILLSERVER = 483

    # :Your connection is restricted!
    ERR_RESTRICTED = 484

    # :You're not the original channel operator
    ERR_UNIQOPPRIVSNEEDED = 485

    # :No O-lines for your host
    ERR_NOOPERHOST = 491

    # :Unknown MODE flag
    ERR_UMODEUNKNOWNFLAG = 501

    # :Cannot change mode for other users
    ERR_USERSDONTMATCH = 502


    # CODES BELOW ARE NOT DEFINED IN THE RFC

    # Used by Rizon when a user has identified for a nick
    # <nick> <nick_logged_in> :is logged in as
    RIZON_RPL_WHOISIDENTIFIED = 330

    # Used by Freenode when a user has identified for a nick
    # <nick> :has identified for this nick
    FREENODE_RPL_WHOISIDENTIFIED = 307

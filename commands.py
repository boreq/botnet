# -*- coding: utf-8 -*-
import os
import fourchan_json
import fourchan_pic
import random
import string
import re
import reddit
import pornhub
import json
import requests
from nltk.tag import pos_tag
import time
import threading
import urllib.parse
from bs4 import BeautifulSoup
from requests_oauthlib import OAuth1Session

class tcol:
        NORMAL = "\u000f"
        BOLD = "\u0002"
        UNDERLINE = "\u001f"
        REVERSE = "\u0016"
        WHITE = "\u00030"
        BLACK = "\u00031"
        DARK_BLUE = "\u00032"
        DARK_GREEN = "\u00033"
        RED = "\u00034"
        BROWN = "\u00035"
        GREEN = "\u00039"


def get_random_line(file_name):
    total_bytes = os.stat(file_name).st_size
    random_point = random.randint(0, total_bytes)
    xfile = open(file_name)
    xfile.seek(random_point)
    c = xfile.read(1)
    s = ""
    while c != ".":
        c = xfile.read(1)

    xfile.read(1)
    c = xfile.read(1)
    while c == ".":
        xfile.read(1)
    while c != ".":
        if c != "\n":
            if c != "\r":
                s += c
            else:
                s += " "
        else:
            s += " "
        c = xfile.read(1)
    s += c
    c = xfile.read(1)
    s += c
    while c == ".":
        s += c
        c = xfile.read(1)
    s.replace("- ", " ")
    s = re.sub('\s+', ' ', s)
    return s


def getuser(ircmsg):
    return ircmsg.split(":")[1].split('!')[0]


_command_dict = {}


def command(name):
    # The decorator appending all fn's to a dict
    def _(fn):
        # Decorators return an inner function whom we
        # pass the function.
        _command_dict[name] = fn
    return _


def nothing(args):
    return ""


def get_command(name):
    # Explicity over implicity?
    # Fuck that

    # We just lower the string.
    # and check later its upper cased
    if name.lower() in _command_dict:
        return _command_dict[name.lower()]
    else:
        return nothing

def random_image(image_link):
    """
    Opens a directory with images using bs4.
    Then picks one value from list of images.
    """
    img_list = []
    soup = BeautifulSoup(requests.get(image_link).text, "html.parser")
    for i in soup.findAll("a"):
        parsed = image_link+i['href']
        img_list.append(parsed)
    img_link = random.choice(img_list)
    return img_link

def imgur_pic(subreddit):
    html = BeautifulSoup(requests.get("http://imgur.com/r/{}/".format(subreddit)).text, "html.parser")
    length = len(html.findAll("a", {"class": "image-list-link"}))
    retval = ""
    try:
        retval = "https://imgur.com{}".format(html.findAll("a", {"class": "image-list-link"})[random.randint(0, length)]['href'])
    except IndexError:
        pass
    return retval

@command("upper")
def upper(args):
    return " ".join(args["args"]).upper()

@command("lower")
def lower(args):
    return " ".join(args["args"]).lower()

@command("echo")
def echo(args):
    return " ".join(args["args"])

@command("ex")
def expand(args):
    return "".join([c + (" ") for c in " ".join(args["args"])]).strip()

@command("mul")
def multiply(args):
    return (" ".join(args["args"][1:]) + " ") * int(args["args"][0])

@command("trunc")
def truncate(args):
    return " ".join(args["args"][1:])[:int(args["args"][0])]

@command("re")
def replace(args):
    replacement = args["args"][0].split("/")
    return " ".join(args["args"][1:]).replace(replacement[0], replacement[1])

@command("sq")
def strip_4chan_quotes(args):

    # sometimes single elements contain multiple words
    complete = " ".join(args["args"]).split(" ")

    # quotes seem to begin with x033
    return " ".join([s for s in complete if not s.startswith("\x033")])

@command("tweet")
def tweet(args):
    if not "twoxy_api_key" in args["config"]:
        return "I haven't been configured to post on Twitter."

    tweet = " ".join(args["args"])
    params = { "tweet" : tweet, "key" : args["config"]["twoxy_api_key"] }

    data = requests.post("https://twoxy.gpunk.net/api/tweet", data=params).json()
    if not "url" in data:
        return "Sorry, I couldn't post your tweet: {}".format(data["message"])
    else:
        return "{}, {}".format(getuser(args["raw"]), data["url"])

@command("tw")
def tw(args):
    return _command_dict["tweet"](args)

@command("center")
def centrist(args):
    return  ("I bet u think u got me cornered, well guess what nerd? IM A"
            " CENTRIST you heard me right. people who hold serious beliefs and"
            " convictions are FUCKING LOSERS")

@command("rms.sexy")
def rms_sexy(args):
    return random_image("https://rms.sexy/img/")

@command("shitpost")
def shitposting(args):  # almost entirely automated shitposting

    shitpost = fourchan_json.get_random_post(args)
    res_shitpost = []
    for l in shitpost.splitlines():
        l = l.strip()
        if l.startswith(">"):
            l = tcol.DARK_GREEN + l + tcol.NORMAL
        res_shitpost.append(l)
    shitpost = " ".join(res_shitpost)

    if args["command"].isupper():
        shitpost = shitpost.upper()
    return shitpost

@command("pic")
def pic(args): #random pic from 4chan for big guys
    new_args = args["args"]
    new_args.append('')
    nick = args["prefix"].split('!')[0]
    random = True
    board_exists = False
    if len(new_args) != 1:
        random = False
        board_exists = fourchan_pic.open_board(new_args[0])
    if board_exists or random:
            response = '{}: {}'.format(nick, fourchan_pic.main(new_args))
            return response

@command("lepic")
def lepic(args):
    new_args = args["args"]
    subreddit = "linuxcirclejerk"
    if new_args:
        subreddit = new_args[0]
    return imgur_pic(subreddit)

@command("le")
def reddit_le(args):
    new_args = args["args"]

    subreddit = "linuxcirclejerk"
    if new_args:
        subreddit = new_args[0]

    try:
        response = reddit.get_random_comment(subreddit)
    except reddit.APIError as e:
        raise e
    except:
        raise Exception('Serious Reddit API error, everything is on fire')

    return " ".join(response.splitlines())

@command("lelong")
def reddit_lelong(args):
    subreddit = "linuxcirclejerk" if len(args["args"]) < 1 else args["args"][0]
    min_length = 200 if len(args["args"]) < 2 else int(args["args"][1])
    try:
        return " ".join(reddit.get_random_comment(subreddit, min_length).splitlines())
    except Exception as e:
        raise Exception("Serious Reddit API error: {}".format(e))

@command("lelast")
def reddit_last_url(args):
    return reddit.last_url

@command("porn")
def pornhub_comment(args):
    return pornhub.get_random_comment()

@command("pornlast")
def pornhub_last_url(args):
    return pornhub.last_url

@command("porntitle")
def pornhub_title_whatever(args):
    return pornhub.get_random_title()

@command("cybhelp")
def halp(args):
    user = getuser(args["raw"])
    string = user + ", sending you a private message of my commands.\n"
    args["sendmsg"](user, "ur a faget")
    return string

@command("interject")
def interjection(args):  # I'd just like to interject for a moment
    str = ("I'd just like to interject for moment. What you're referring to as "
              "Linux, is in fact, GNU/Linux, or as I've recently taken to calling it,"
              " GNU plus Linux. ​http://pastebin.com/2YxSM4St\n")
    return str

@command("git")
def git(args):
    str = "​https://github.com/cybits/cybot What are we going to do on the repo? waaaah fork =3\n"
    return str

@command("reminder")
def reminder(args):  # today, I will remind them
    return ('Remember to fix your posture :D http://gateway.ipfs.io/ipfs/QmR91KZ77KMg1h8HqBTxtHNZiWCECiXhHkTR7coVqyyFvF/posture.jpg\n')

@command("memearrows")
def memearrows(args):  # >implying you can triforce
    str = ("Meme arrows are often used to preface implications or feels. See "
              "also: implying, feel.\n")
    return str


@command("int")
def intensifies(args):  # [python intensifies]
    if args["args"]:
        ret = "[" + " ".join(args["args"]) + " intensifies]\n"
    else:
        ret = "[no argument intensifies]\n"
    if args["command"].isupper():
        return ret.upper()
    else: return ret


@command("ayylmao")
def ayylmao(args):
    sendmsg = args["sendmsg"]
    line = ('ABDUCTION: INCOMING')

    ayylien = ["       .-""""-.        .-""""-.    ",
               "      /        \      /        \   ",
               "     /_        _\    /_        _\  ",
               "    // \      / \\  // \      / \\ ",
               "    |\__\    /__/|  |\__\    /__/| ",
               "     \    ||    /    \    ||    /  ",
               "      \        /      \        /   ",
               "       \  __  /        \  __  /    ",
               "        '.__.' ayy lmao '.__.'     "]


    ircmsg = args["raw"]
    user = ircmsg.split(":")[1].split('!')[0]
    channel = args["channel"]
    sendmsg(channel, line)
    for lines in ayylien:
        sendmsg(user, lines)
        time.sleep(1)
   # ayy lmao
   # Doing all the logic inside the function
   # Since sendmsg wont post empty strings.
    return ""

@command("feel")
def feel(args):  # >tfw
    sendmsg = args["sendmsg"]
    line = ('"tfw no gf" is an abbreviated expression for "that feeling [I get] '
              'when [I have] no girlfriend" often used in online discussions and '
              'comments.')

    feelguy  = ["░░░░░░░▄▀▀▀▀▀▀▀▀▀▀▄▄░░░░░░░░░",
                "░░░░▄▀▀░░░░░░░░░░░░░▀▄░░░░░░░",
                "░░▄▀░░░░░░░░░░░░░░░░░░▀▄░░░░░",
                "░░█░░░░░░░░░░░░░░░░░░░░░▀▄░░░",
                "░▐▌░░░░░░░░▄▄▄▄▄▄▄░░░░░░░▐▌░░",
                "░█░░░░░░░░░░░▄▄▄▄░░▀▀▀▀▀░░█░░",
                "▐▌░░░░░░░▀▀▀▀░░░░░▀▀▀▀▀░░░▐▌░",
                "█░░░░░░░░░▄▄▀▀▀▀▀░░░░▀▀▀▀▄░█░",
                "█░░░░░░░░░░░░░░░░▀░░░▐░░░░░▐▌",
                "▐▌░░░░░░░░░▐▀▀██▄░░░░░░▄▄▄░▐▌",
                "░█░░░░░░░░░░░▀▀▀░░░░░░▀▀██░▀▄",
                "░▐▌░░░░▄░░░░░░░░░░░░░▌░░░░░░█",
                "░░▐▌░░▐░░░░░░░░░░░░░░▀▄░░░░░█",
                "░░░█░░░▌░░░░░░░░▐▀░░░░▄▀░░░▐▌",
                "░░░▐▌░░▀▄░░░░░░░░▀░▀░▀▀░░░▄▀░",
                "░░░▐▌░░▐▀▄░░░░░░░░░░░░░░░░█░░",
                "░░░▐▌░░░▌░▀▄░░░░▀▀▀▀▀▀░░░█░░░",
                "░░░█░░░▀░░░░▀▄░░░░░░░░░░▄▀░░░",
                "░░▐▌░░░░░░░░░░▀▄░░░░░░▄▀░░░░░",
                "░▄▀░░░▄▀░░░░░░░░▀▀▀▀█▀░░░░░░░",
                "▀░░░▄▀░░░░░░░░░░▀░░░▀▀▀▀▄▄▄▄▄"]


    ircmsg = args["raw"]
    user = ircmsg.split(":")[1].split('!')[0]
    channel = args["channel"]
    sendmsg(channel, line)
    for lines in feelguy:
        sendmsg(user, lines)
        time.sleep(1)
    # Doing all the logic inside the function
    # Since sendmsg wont post empty strings.
    return ""

@command("wake")
def wake(args):
    return "(can't wake up)"

# TODO: Use this for something
def autointerject(args):  # making sure users don't forget the GNU
    str1 = ("I'd just like to interject for moment. What you're referring to as Linux, is in fact, "
            "GNU/Linux.\n")

    str2 = ("I'd just like to interject for moment. What you're referring to as Linux, is "
            "in fact, GNU/Linux, or as I've recently taken to calling it, GNU plus Linux. Linux "
            "is not an operating system unto itself, but rather another free component of a fully"
            " functioning GNU system made useful by the GNU corelibs, shell utilities and vital "
            "system components comprising a full OS as defined by POSIX.\n"
            "Many computer users run a modified version of the GNU system every day, "
            "without realizing it. Through a peculiar turn of events, the version of GNU "
            "which is widely used today is often called Linux, and many of its users are not"
            " aware that it is basically the GNU system, developed by the GNU Project.\n"
            "There really is a Linux, and these people are using it, but it is just a "
            "part of the system they use. Linux is the kernel: the program in the system "
            "that allocates the machine's resources to the other programs that you run. "
            "The kernel is an essential part of an operating system, but useless by "
            "itself; it can only function in the context of a complete operating "
            "system.\n"
            "Linux is normally used in combination with the GNU operating system: the "
            "whole system is basically GNU with Linux added, or GNU/Linux. All the "
            "so-called Linux distributions are really distributions of GNU/Linux!\n")

    return str1, str2


@command("implying")
def implying(args):  # >implying this needs a comment
    return ('>implying is used in a mocking manner to challenge an "implication" '
            'that has been made, or sometimes it can be simply used as a joke in '
            'itself.\n')


@command("lit")
def sentence(args):  # This function grabs a random sentence from a txt file and posts it to the channel
    directory = os.path.dirname(__file__)
    directory = directory + os.path.join("/texts/books/")
    line = directory + os.path.join(random.choice(os.listdir(directory)))
    return get_random_line(line) + "\n"
    # return get_random_line(random.choice(os.listdir("/home/polaris/PycharmProjects/cybot/texts/"))) + "\n"

@command("guinea")
def guinea(args):
    directory = os.path.dirname(__file__)
    guinea = directory + os.path.join("/texts/other/guinea.txt")
    return random.choice(list(open(guinea)))

@command("guineas")
def guineas(args):
    return imgur_pic("guineapigs")

@command("cat")
def cat(args):
    return imgur_pic("cats")

@command("rat")
def rat(args):
    return imgur_pic("rats")

@command("checkem")
def checkem(args):
    not_dubs = random.randint(0, 99)
    return str(not_dubs).zfill(2)

@command("terry")
def terry(args):  # Grabs a random Terry quote from the 9front list
    directory = os.path.dirname(__file__)
    terry = directory + os.path.join("/texts/other/terry.txt")
    return random.choice(list(open(terry)))

@command("rob")
def pike(args):
    directory = os.path.dirname(__file__)
    pike = directory + os.path.join("/texts/other/rob.txt")
    return random.choice(list(open(pike)))

@command("larry")
def lwall(args):
    directory = os.path.dirname(__file__)
    wall = directory + os.path.join("/texts/other/larry.txt")
    return random.choice(list(open(wall)))

@command("gene")
def ray(args):
    directory = os.path.dirname(__file__)
    ray = directory + os.path.join("/texts/other/timecube.txt")
    return random.choice(list(open(ray)))

@command("linus")
def torv(args):
    directory = os.path.dirname(__file__)
    torv = directory + os.path.join("/texts/other/linus.txt")
    return random.choice(list(open(torv)))

@command("rms")
def stallman(args):
    directory = os.path.dirname(__file__)
    richard = directory + os.path.join("/texts/other/stallman.txt")
    return random.choice(list(open(richard)))

@command("eightball")
def eight(args):
    directory = os.path.dirname(__file__)
    eight = directory + os.path.join("/texts/other/eightball.txt")
    return random.choice(list(open(eight)))

@command("lewd")
def lewd(args):
    directory = os.path.dirname(__file__)
    lewd = directory + os.path.join("/texts/other/lewd.txt")
    return random.choice(list(open(lewd)))

@command("smug")
def smug(args):
    directory = os.path.dirname(__file__)
    smug = directory + os.path.join("/texts/other/smug.txt")
    return random.choice(list(open(smug)))

@command("joerogan")
def joerogan(args):
    sendmsg = args["sendmsg"]
    channel = args["channel"]
    if random.randrange(1,5) == 3: # chosen by fair dice roll.
                                   # guaranteed to be random.
        intromsg = [
            "THIS IS YOUR DAILY REMINDER TO PLUG IN YOUR BLENDERS, HEAT UP YOUR FLOTATION TANKS TO SKIN TEMP (35.5*C)",
            "THE WEED HAS BEEN LIT AND IT'S TIME TO SLAM YOUR KALE SHAKES, TAKE A TOKE & MARK OFF YOUR CHECKLIST TO POP YOUR:",
            "ALPHA BRAIN",
            "SHROOMTECH",
            "KRILL & MCT OIL",
            "PRIMATE CARE PILLS",
            "​https://www.youtube.com/watch?v=22GjkJw0WXk <---- HIT PLAY NIGGA"]
        for msg in intromsg:
            sendmsg(channel, msg)
            time.sleep(1)
        return ""
    else:
        directory = os.path.dirname(__file__)
        joerogan = directory + os.path.join("/texts/other/joerogan.txt")
        l = random.choice(list(open(joerogan)))
        l = l.strip()
        if l.startswith(">"):
            l = tcol.DARK_GREEN + l + tcol.NORMAL
        return l

@command("triforce")
def coolt(args):
    sendmsg = args["sendmsg"]
    channel = args["channel"]
    spaces1 = random.randint(1,5)
    spaces2 = random.randint(1,3)
    string1 = (" "*spaces1 + ("▲"))
    string2 = (" "*spaces2 + ("▲ ▲"))
    sendmsg(channel, string1)
    sendmsg(channel, string2)
    return ""

@command("booty")
def booty(args):
    return "( ͡° ͜ʖ ͡°)"


@command("shrug")
def shrug(args):
    return "¯\_(ツ)_/¯"

@command("denko")
def denko(args):
    return "(´･ω･`)"


@command("cute")
def cute(args):
    user = getuser(args["raw"])
    args = args["args"]
    if len(args) < 1:
        cutelist = ["✿◕ ‿ ◕✿", "❀◕ ‿ ◕❀", "(✿◠‿◠)",
                    "(◕‿◕✿) ", "( ｡◕‿◕｡)", "(◡‿◡✿)",
                    "⊂◉‿◉つ ❤", "{ ◕ ◡ ◕}", "( ´・‿-) ~ ♥",
                    "(っ⌒‿⌒)っ~ ♥", "ʕ´•ᴥ•`ʔσ”", "(･Θ･) caw",
                    "(=^･ω･^)y＝", "ヽ(=^･ω･^=)丿", "~(=^･ω･^)ヾ(^^ )",
                    "| (•□•) | (❍ᴥ❍ʋ)", "ϞϞ(๑⚈ ․̫ ⚈๑)∩", "ヾ(･ω･*)ﾉ",
                    "▽・ω・▽ woof~", "(◎｀・ω・´)人(´・ω・｀*)", "(*´・ω・)ノ(-ω-｀*)",
                    "(❁´ω`❁)", "(＊◕ᴗ◕＊)", "{´◕ ◡ ◕｀}", "₍•͈ᴗ•͈₎",
                    "(˘･ᴗ･˘)", "(ɔ ˘⌣˘)˘⌣˘ c)", "(⊃｡•́‿•̀｡)⊃", "(´ε｀ )♡",
                    "(◦˘ З(◦’ںˉ◦)♡", "( ＾◡＾)っ~"
                    "╰(　´◔　ω　◔ `)╯", "(*･ω･)", "(∗•ω•∗)", "( ◐ω◐ )"]
    else:
        args = " ".join(args)
        cutelist = ["(✿◠‿◠)っ~ ♥ " + args, "⊂◉‿◉つ ❤ " + args, "( ´・‿-) ~ ♥ " + args,
                    "(っ⌒‿⌒)っ~ ♥ " + args, "ʕ´•ᴥ•`ʔσ” BEARHUG " + args,
                    user + " ~(=^･ω･^)ヾ(^^ ) " + args, user + " (◎｀・ω・´)人(´・ω・｀*) " + args,
                    user + " (*´・ω・)ノ(-ω-｀*) " + args,
                    user + " (ɔ ˘⌣˘)˘⌣˘ c) " + args,
                    "(⊃｡•́‿•̀｡)⊃ U GONNA GET HUGGED " + args, args + " (´ε｀ )♡",
                    user + " (◦˘ З(◦’ںˉ◦)♡ " + args, "( ＾◡＾)っ~ ❤ " + args]
    return random.choice(cutelist)

@command("bots")
def bots(args):
    return "Reporting in! [Python] Try .cybhelp for commands."

@command("spikepig")
def spikepig(args):
    return imgur_pic("hedgehog")

@command("r8")
def random_rate(args):
    message = args["args"]
    give_rating = random.randint(0, 1)
    message = pos_tag(message)
    print(message)
    nounlist = []
    for word, tag in message:
        if tag == "NNP" or tag == "NN":
            nounlist.append(word)
    if not nounlist:
        nounlist.append("nothings")
    word = nounlist[random.randint(0, len(nounlist)-1)]
    rating = random.randint(0, 10)
    if give_rating or nounlist[0] == "nothings":
        return str(rating) + "/10"
    else:
        return word + "/10"

@command("decide")
def random_option(args):
    return random.choice(re.split(", | or "," ".join(args["args"])))

@command("hackers")
def hackers(args):
    directory = os.path.dirname(__file__)
    hackers = directory + os.path.join("/texts/other/hackers.txt")
    return random.choice(list(open(hackers)))

@command("deusex")
def deusex(args):
    directory = os.path.dirname(__file__)
    deusex = directory + os.path.join("/texts/other/deusex.txt")
    return random.choice(list(open(deusex)))

@command("noided")
def noided(args):
    directory = os.path.dirname(__file__)
    noided = directory + os.path.join("/texts/other/grips.txt")
    return random.choice(list(open(noided)))

@command("2070")
def samhyde(args):
    directory = os.path.dirname(__file__)
    noided = directory + os.path.join("/texts/other/2070.txt")
    return random.choice(list(open(noided)))

@command("eu")
def eu(args):
    directory = os.path.dirname(__file__)
    noided = directory + os.path.join("/texts/other/eu.txt")
    return random.choice(list(open(noided)))

@command("just")
def just(args):
    return "...type it yourself..."

@command("spooky")
def spooky(args):
    directory = os.path.dirname(__file__)
    spook = directory + os.path.join("/texts/other/spooks.txt")
    return random.choice(list(open(spook)))

def breaklines(str):  # This function breaks lines at \n and sends the split lines to where they need to go
    strarray = string.split(str, "\n")
    return strarray

@command("ba")
def ba(args):
    #define a user agent
    user_agent = {'User-Agent': 'Mozilla/5.0 (Windows NT 6.1; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/40.0.2214.85 Safari/537.36'}
    baseurl = "http://www.beeradvocate.com"
    if args["args"]:
        try:
            int(args["args"][-1])
            payload = {"q" : " ".join(args["args"][:-1])}
        except ValueError:
            payload = {"q" : " ".join(args["args"])}
        r = requests.get(baseurl + "/search/", headers=user_agent, params=payload)
        if r.status_code == 200:
            soup = BeautifulSoup(r.text, "html.parser")
            regex = re.compile("/beer/profile/.*/.+")
            beers = [b.get("href") for b in soup.find_all(href=regex)]
            if len(beers) > 0:
                data = beer_lookup(baseurl+beers[0], user_agent)
                msg = [
                        data['name'] + " | " + data['style'],
                        "BA score: " + data['ba_score'] + " (From: " + data['ba_ratings'] + ") | Bro score: " + data['bro_score'],
                        data['brewery'] + " | " + data['abv'],
                        "!" + baseurl + beers[0]
                ]
                to_send = []
                for line in msg:
                    to_send.append(line)
                return " | ".join(to_send)

            else:
               return "No results from BA."

# BA helper function.
def beer_lookup(url, user_agent):
    r = requests.get(url, headers=user_agent)
    if r.status_code == 200:
        soup = BeautifulSoup(r.text, "html.parser")
        # Stupid shit because ABV is just a barewords string somewhere in the div.
        rightdiv = soup.find('div', style="float:right; width:70%;")
        strsoup  = str(rightdiv.contents[5]).splitlines()
        info = {}
        info['name']       = str(soup.title.string.split("|")[0])
        info['ba_score']   = soup.find('span', class_="BAscore_big ba-score").contents[0]
        info['ba_class']   = soup.find('span', class_="ba-score_text").contents[0]
        info['ba_ratings'] = soup.find('span', class_="ba-ratings").contents[0]
        info['bro_score']  = soup.find('span', class_="BAscore_big ba-bro_score").contents[0]
        info['brewery']    = soup.select('span[itemprop="title"]')[2].contents[0]
        info['style']      = soup.find('a',href=re.compile("\/beer\/style\/\d+")).contents[0].contents[0]
        info['abv']        = strsoup[7].split("</b>")[1].lstrip()
        return info

@command("bash")
def bash(args):
    baseurl = "http://bash.org"
    user_agent = {'User-Agent': 'Mozilla/5.0 (Windows NT 6.1; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/40.0.2214.85 Safari/537.36'}
    url = baseurl + "/?random1"
    r = requests.get(url, headers=user_agent)

    if r.status_code != 200:
        return

    soup = BeautifulSoup(str(r.content,'UTF-8',errors='replace'), "html.parser")
    quotes = soup.findAll('p', class_ = "qt")

    if len(quotes) == 0:
        return "No quotes found"

    for i in range(len(quotes)):
        quote = quotes[i].text.strip()
        quote_s = quote.split("\r\n")
        if len(quote_s) == 1:
            return quote_s[0]

@command("ut")
def ut(args):
    baseurl = "https://www.untappd.com"
    user_agent = {'User-Agent': 'Mozilla/5.0 (Windows NT 6.1; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/40.0.2214.85 Safari/537.36'}
    if len(args["args"]) == 0:
        return
    query_string = urllib.parse.urlencode({"q":" ".join(args["args"])})
    r = requests.get(baseurl + "/search?" + query_string, headers=user_agent)

    if r.status_code != 200:
        return

    soup = BeautifulSoup(str(r.content,'UTF-8',errors='replace'), "html.parser")
    beers = soup.findAll('div', class_="beer-item")

    if len(beers) == 0:
        return "No beers"

    beer = beers[0]

    # Shiny fucking penny to anyone that makes this not shit
    # It's quite defensive, we never know if a beer actually won't have any of these fields
    name = beer.find('p',class_='name').text if beer.find('p',class_='name') else '-'
    brewery = beer.find('p',class_='brewery').text if beer.find('p',class_='brewery') else '-'
    style = beer.find('p',class_='style').text if beer.find('p',class_='style') else '-'
    abv = beer.find('p',class_='abv').text.strip() if beer.find('p',class_='abv') else '-'
    ibu = beer.find('p',class_='ibu').text.strip() if beer.find('p',class_='ibu') else '-'
    url = "!" + baseurl+beer.a['href']
    score_span = beer.find('span',class_='num')
    if score_span:
        score = 'Score: ' + score_span.text[1:-1]
    else:
        score = 'Score: -'

    return " | ".join([name,style,brewery,score,abv,ibu,url])

# in place case-preserving function
def replacement_func(match, repl_pattern):
    match_str = match.group(0)
    repl = ''.join([r_char if m_char.islower() else r_char.upper()
                   for r_char, m_char in zip(repl_pattern, match_str)])
    repl += repl_pattern[len(match_str):]
    return repl

bicd ={"epic":"ebin",
        "penis":"benis",
        "wh":"w",
        "th":"d",
        "af":"ab",
        "ap":"ab",
        "ca":"ga",
        "ck":"gg",
        "co":"go",
        "ev":"eb",
        "ex":"egz",
        "et":"ed",
        "iv":"ib",
        "it":"id",
        "ke":"ge",
        "op":"ob",
        "ot":"od",
        "po":"bo",
        "pe":"be",
        "pi":"bi",
        "up":"ub",
        "va":"ba",
        "cr":"gr",
        "kn":"gn",
        "lt":"ld",
        "mm":"m",
        "nt":"dn",
        "pr":"br",
        "tr":"dr",
        "bs":"bz",
        "ds":"dz",
        "fs":"fz",
        "gs":"gz",
        "is":"iz",
        "ls":"lz",
        "ms":"mz",
        "ns":"nz",
        "rs":"rz",
        "ss":"sz",
        "ts":"tz",
        "us":"uz",
        "ws":"wz",
        "ys":"yz",
        "alk":"olk",
        "ing":"ign",
        "ic":"ig",
        "ng":"nk",
        "kek":"geg",
        "some":"sum",
        "meme":"maymay"
}
ebinFaces = [ ':D', ':DD', ':DDD', ':-D', 'XD', 'XXD', 'XDD', 'XXDD' ];
@command("spurd")
def spurd(args):
    new_args = " ".join(args["args"])
    for k, v in bicd.items():
            new_args = re.sub(k, lambda k: replacement_func(k,v), new_args, flags=re.I)
    return new_args+" "+ random.choice(ebinFaces)

@command("1337")
def leetspeak(args):
    input = " ".join(args["args"])

    if input.strip() == "":
        input = random.choice(["elite", "leet", "hacks", "hax", "cyb as fuck"])

    # adapted from
    # https://scripts.irssi.org/scripts/dau.pl
    # line 2943
    output = re.sub(r'fucker', 'f@#$er', input, flags=re.I|re.U)
    output = re.sub(r'hacker', 'h4x0r', output, flags=re.I|re.U)
    output = re.sub(r'sucker', 'sux0r', output, flags=re.I|re.U)
    output = re.sub(r'fear', 'ph34r', output, flags=re.I|re.U)

    output = re.sub(r'\b(?P<q>\w+)ude\b', r'\g<q>00d', output, flags=re.I|re.U)
    output = re.sub(r'\b(?P<q>\w+)um\b', r'\g<q>00m', output, flags=re.I|re.U)
    output = re.sub(r'\b(?P<q>\w{3,})er\b', r'\g<q>0r', output, flags=re.I|re.U)
    output = re.sub(r'\bdo\b', r'd00', output, flags=re.I|re.U)
    output = re.sub(r'\bthe\b', r'teh', output, flags=re.I|re.U)
    output = re.sub(r'\byou\b', r'j00', output, flags=re.I|re.U)

    output = output.translate(str.maketrans("lLzZeEaAsSgGtTbBqQoOiIcC", "11223344556677889900||(("))
    if random.randrange(0,2) == 1:
        output = output.lower()
    else:
        output = output.upper()
    return output


@command("stump")
def trump(args):
    s = []
    s.append("I'm the best meme for america. Kek says so. Top person. VERY high "\
            "energy. Would god king kek lie about such a thing? Of course not.")
    s.append("I don't even want to talk about %s. Just look at his numbers. He's " \
            "a very low-energy person.")
    s.append("People come to me and tell me, they say, \"Donald, we like you, but" \
           " there's something weird about %s.\" It's a very serious problem.")
    s.append("We have incompetent people, they are destroying this country, and " \
           "%s doesn't have what we need to make it great again.")
    s.append("Nobody likes %s, nobody in Congress likes %s, nobody likes %s anywh" \
           "ere once they get to know him.")
    s.append("%s is an embarrassment to himself and his family, and the Republica" \
            "n Party has essentially -- they're not even listening to %s.")
    s.append("Look, here's the thing about %s. We're losing in all of our deals, " \
            "we're losing to Mexico, we're losing with China, and I'm sure ther" \
            "e are some good ones, but %s has to go back.")
    s.append("What are they saying? Are those %s people? Get 'em outta here! Get " \
            "'em out! Confiscate their coats!")
    s.append("Donald J. Trump is calling for a total and complete shutdown of %s " \
            "entering the United States.")
    s.append("Did you read about %s? No more \"Merry Christmas\" at %s's house. N" \
            "o more. Maybe we should boycott %s.")
    s.append("Look at that face! Would anyone vote for that? Can you imagine that" \
            ", %s, the face of our next president?")
    s.append("We have to have a wall. We have to have a border. And in that wall" \
            " we're going to have a big fat door where people can come into the" \
            " country, but they have to come in legally and those like %s who a" \
            "re here illegally will have to go back.")
    s.append("%s, you haven't been called, go back to Univision.")
    s.append("%s? You could see there was blood coming out of %s's eyes. Blood c" \
            "oming out of %s's... wherever.")
    s.append("%s is not a war hero. He's a war hero because he was captured? I l" \
            "ike people who weren't captured.")
    s.append("When Mexico sends its people, they're not sending the best. They'r" \
            "e sending people like %s that have lots of problems and they're br" \
            "inging those problems. They're bringing drugs, they're bringing cr" \
            "ime. They're rapists and some, I assume, are good people, but I sp" \
            "eak to border guards and they're telling us what we're getting.")
    s.append("I thought that was disgusting. That showed such weakness, the way " \
            "%s was taken away by two young women, the microphone; they just to" \
            "ok the whole place over. That will never happen with me. I don't " \
            "know if I'll do the fighting myself or if other people will, but t" \
            "hat was a disgrace. I felt badly for %s. But it showed that he's w" \
            "eak.")
    s.append("%s is an enigma to me. He said that he's \"pathological\" and that" \
            " he's got, basically, pathological disease... I don't want a perso" \
            "n that's got pathological disease.")
    s.append("The concept of global warming was created by and for %s in order t" \
            "o make U.S. manufacturing non-competitive.")
    s.append("The U.S. will invite %s, the Mexican criminal who just escaped pri" \
            "son, to become a U.S. citizen because our \"leaders\" can't say no" \
            "!")
    s.append("You want to know what will happen? The wall will go up and %s will" \
            " start behaving.")
    s.append("Our great African American President hasn't exactly had a positive" \
            " impact on the thugs like %s who are so happily and openly destroy" \
            "ing Baltimore!")
    s.append("%s is a weak and ineffective person. He's also a low-energy person" \
            ", which I've said before. ... If he were president, it would just " \
            "be more of the same. He's got money from all of the lobbyists and " \
            "all of the special interests that run him like a puppet.")
    s.append("%s is weak on immigration and he’s weak on jobs. We need someone w" \
            "ho is going to make the country great again, and %s is not going t" \
            "o make the country great again.")
    s.append("I will build a great wall -- and nobody builds walls better than m" \
            "e, believe me -- and I'll build them very inexpensively. I will bu" \
            "ild a great, great wall on our southern border, and I will make %s" \
            " pay for that wall. Mark my words.")
    s.append("The other candidates -- like %s -- they went in, they didn't know " \
            "the air conditioning didn't work. They sweated like dogs... How ar" \
            "e they gonna beat ISIS? I don't think it's gonna happen.")
    stumpee = " ".join(args["args"])
    if stumpee.lower() == "trump":
        return "You can't stump the Trump"
    selection = random.randint(0, 24)
    return s[selection].replace("%s", stumpee)

@command("thewire")
def thewire(args):
    wire = os.path.dirname(__file__) + "/texts/other/thewire.txt"
    return random.choice(list(open(wire)))

@command("np")
def librefm(args):
    libreuser = ""
    if len(args["args"]) == 0:
        libreuser = args["prefix"].split('!')[0]
    else:
        libreuser = args["args"][0]
    xml = BeautifulSoup(requests.get("https://libre.fm/2.0/?method=user.getrecenttracks&user={}&page=1&limit=1".format(libreuser)).text, "html.parser")
    try:
        try:
            if xml.lfm.recenttracks.track['nowplaying']:
                return "User {} is now playing \"{}\" by {} on [{}].".format(libreuser,xml.lfm.recenttracks.find('name').string,xml.lfm.recenttracks.artist.string,xml.lfm.recenttracks.album.string)
        except KeyError:
                return "User {} last played \"{}\" by {} on [{}].".format(libreuser,xml.lfm.recenttracks.find('name').string,xml.lfm.recenttracks.artist.string,xml.lfm.recenttracks.album.string)
    except:
        return "User {} does not exist on libre.fm.".format(libreuser)

import json
import urllib
import random
import sys
from html.parser import HTMLParser


class MLStripper(HTMLParser):
        def __init__(self):
                super().__init__()
                self.reset()
                self.fed = []

        def handle_data(self, d):
                self.fed.append(d)

        def get_data(self):
                return ''.join(self.fed)


def strip_tags(html):
        s = MLStripper()
        print("html", html)
        s.feed(html)
        print("get data", s.get_data())
        return s.get_data()


def formattext(text):
        text = text.replace("<br>", "\n")
        text = text.replace("&gt;", ">")
        text = text.replace("&#039;", "'")
        text = strip_tags(text)
        return text


def write(text):
        sys.stdout.write(text)


def is_number(s):
    try:
        float(s)
        return True
    except ValueError:
        return False


def get_boards_json():
    response = urllib.request.urlopen("http://a.4cdn.org/boards.json")
    return json.loads(response.read().decode('utf-8'))


def get_page_json(board, pageindex):
    return json.loads(((urllib.request.urlopen("http://a.4cdn.org/" + board + "/" + str(pageindex) + ".json")).read().decode('utf-8')))


def get_thread_json(board, threadno):
    return json.loads((urllib.request.urlopen("http://a.4cdn.org/" + board + "/thread/" + str(threadno) + ".json")).read().decode('utf-8'))


def get_op_no(pagedata, threadindex):
    return pagedata['threads'][threadindex]['posts'][0]['no']

def get_random_post(args):

    for iterations in range(0, 10):
        data = get_boards_json()
        allboards = data['boards']

        found = False

        if args['args']:
            i = 0
            for board in allboards:
                i += 1
                if args['args'][-1:][0] in board['meta_description'].split()[0].split('&quot;')[-1:]:
                    found = True
                    i -= 1
                    break

        if not found:
            i = random.randint(0, len(allboards)-1)

        board = allboards[i]['board']
        numpages = allboards[i]['pages']

        i = random.randint(1, numpages)

        pagedata = get_page_json(board, i)
        threads = pagedata['threads']
        numthreads = len(threads)

        i = random.randint(0, numthreads-1)

        threadno = get_op_no(pagedata, i)
        thread = get_thread_json(board, threadno)

        j = random.randint(0, len(thread['posts'])-1)

        postinfo = json.dumps(thread['posts'][j])

        try:
            if 'com' in postinfo and 'sticky' not in postinfo:
                content = thread['posts'][j]['com']
                text = (formattext(content))

                if len(text) > 1 and not text[2:].isdigit():
                    final = text
                    return final
                else:
                    get_random_post(args)

            elif iterations == 10:
                return "No shitpost found."

            else:
                get_random_post(args)
        except:
            return "No random post for you"

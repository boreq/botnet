import requests
import random
from bs4 import BeautifulSoup

base_url = 'https://pornhub.com'
last_url = ''

class APIError(Exception):
    pass

def get(url, no_cache=False):
    headers = {
        'User-Agent': 'cybits a cute IRC bot',
    }
    if no_cache:
        headers['Cache-Control'] = 'private,max-age=0'
    return requests.get(base_url + url, headers=headers)

# Fetch comments from a given pornhub page (or a random one if unspecified)
def get_comments(url):
    comments = []
    tries = 0
    while len(comments) < 2:
        if tries > 5:
            return ["Too many attempts"]
        print("Getting...")
        r = get(url)
        soup = BeautifulSoup(str(r.content, 'UTF-8', errors='replace'))
        comments = soup.findAll('div', class_='commentMessage')
        if comments is None:
            print("bloop")
            comments = []
        tries += 1

    comments.pop()
    comments_sanitised = list(map(lambda x : x.find('span').text,comments))
    global last_url
    last_url = r.url
    return comments_sanitised

def get_random_comment(url = '/random'):
    comments = get_comments(url)
    return random.choice(comments)

def get_random_title():
    r = get('/random')
    soup = BeautifulSoup(str(r.content, 'UTF-8', errors='replace'))
    last_url = r.url
    return soup.find('title').text.split(' - Pornhub.com')[0]

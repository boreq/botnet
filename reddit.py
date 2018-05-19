import requests
import random
import re

api_url = 'https://reddit.com'
last_url = ''

class APIError(Exception):
    pass

def get(url, no_cache=False):
    headers = {
        'User-Agent': 'cybits a cute IRC bot',
    }
    if no_cache:
        headers['Cache-Control'] = 'private,max-age=0'
    return requests.get(api_url + url, headers=headers)

def normify_url(url):
    return api_url + re.sub('\.json.*$','',url)

def get_hot_posts(subreddit):
    """Returns a raw JSON response containing hot posts for the specified
    subreddit from the API.
    """
    url = '/r/%s/hot.json' % subreddit
    r = get(url)
    r.raise_for_status()
    return r.json()

def extract_random_comment(post, min_length=None):
    """Performs an additional API query in order to extract a random post from
    a post. Post parameter should be a data field of a result of a call to
    get_hot_posts.
    """
    url = '%s.json?sort=random' % post['permalink'].rstrip('/')
    r = get(url)
    r.raise_for_status()
    j = r.json()
    comments = [c for c in j[1]['data']['children'] if 'body' in c['data'] and
            not 'I am a bot' in c['data']['body']]
    if min_length:
        comments = [c for c in comments if len(c['data']['body']) >= min_length]
    if len(comments) > 0:
        global last_url
        last_url = normify_url(url)
        return comments[0]
    else:
        raise APIError('The selected post doesn\'t have any comments')

def get_random_comment(subreddit, min_length=None):
    """Returns a text of a random comment from a specified subreddit (for
    a certain value of random).
    """
    # Get the hot posts.
    p = get_hot_posts(subreddit)
    posts = p['data']['children']
    if len(posts) == 0:
        raise APIError('This subreddit contains no posts')

    # Iterate over the random permutation of the hot posts and attempt to
    # select a random comment.
    random.shuffle(posts)
    for post in posts:
        if post['data']['num_comments'] > 0:
            try:
                c = extract_random_comment(post['data'], min_length)
                return c['data']['body']
            except APIError:
                # This will be a predicatable error: no comments (maybe they
                # were removed between queries) so we can just carry on
                pass
    raise APIError('Could not find any comments in the top posts')

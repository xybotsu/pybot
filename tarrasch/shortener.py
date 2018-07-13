import urllib.parse

import requests

def shorten_url(url):
    r = requests.get('http://is.gd/create.php?format=simple&url={}'.format(urllib.parse.quote(url)))
    r.raise_for_status()
    return r.text

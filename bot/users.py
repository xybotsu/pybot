from .config import SLACK_TOKEN
from slackclient import SlackClient
from typing import Dict

slack = SlackClient(SLACK_TOKEN)

_USER_CACHE: Dict[str, object] = {}


def getUser(user_id):
    # store a cache of userId -> userName mappings,
    # so we don't need to make API calls every time
    if not _USER_CACHE.get(user_id):
        _USER_CACHE[user_id] = slack.api_call(
            'users.info', user=user_id)['user']
    return _USER_CACHE[user_id]

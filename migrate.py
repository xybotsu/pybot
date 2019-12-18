import json
import pickle
from bot.redis import redis
import unicodedata
from datetime import datetime
from crypto.CryptoTrader import User, user_to_json, json_to_user, as_user
from typing import Dict, List


def pickle_to_json(prefix: str) -> List[List[str]]:
    game = [
        [account, pickle.loads(redis.get(account))]
        for account in [
            account.decode('utf-8')
            for account in redis.keys('{}.*'.format(prefix))
        ]
    ]

    return [
        [account, user_to_json(user)]
        for [account, user] in game
    ]


def sync_json(prefix: str) -> None:
    for [account, j] in pickle_to_json(prefix):
        user_name = account.split('.')[-1]
        new_prefix = '.'.join(account.split('.')[0:-1]) + '.json'
        new_key = '{}.{}'.format(new_prefix, user_name)
        redis.set(
            new_key,
            j
        )


# syncs pickled data -> json data for all users in prefix
# sync_json('cryptoTrader.test')

# redix key prefix -> List[User]
def hydrate_json(prefix: str) -> List[User]:
    return [
        json_to_user(redis.get(account))
        for account in redis.keys('{}.*'.format(prefix))
    ]


print(
    hydrate_json('cryptoTrader.test.json')
)

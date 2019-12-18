import json
import pickle
from bot.redis import redis
import unicodedata
from datetime import datetime
from crypto.CryptoTrader import User, user_to_json, as_user
from typing import Dict, List

print(json)
print(pickle)
print(redis)


def pickle_to_json(prefix: str) -> List[List[str]]:
    game = [
        [prefix, account, pickle.loads(redis.get(account))]
        for account in [
            account.decode('utf-8')
            for account in redis.keys('{}.*'.format(prefix))
        ]
    ]

    return [
        [prefix, account, user_to_json(user)]
        for [prefix, account, user] in game
    ]


def sync_json(prefix: str) -> None:
    for [prefix, account, j] in pickle_to_json(prefix):
        print(prefix, account)
        # redis.set(
        #     '.json.{}'.format(account),
        #     j
        # )

# def json_to_game(j: str) -> Dict[str, User]:
#     d = json.loads(j, object_hook=as_user)
#     return {
#       k: json.loads()
#     }


"cryptoTrader.albert.foo".


sync_json('cryptoTrader.test')

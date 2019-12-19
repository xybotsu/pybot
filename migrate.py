import json
import pickle
from bot.redis import redis
import unicodedata
from datetime import datetime
from crypto.CryptoTrader import User
from typing import Dict, List


# def pickle_to_json(prefix: str) -> List[List[str]]:
#     game = [
#         [account, pickle.loads(redis.get(account))]
#         for account in [
#             account.decode('utf-8')
#             for account in redis.keys('{}.*'.format(prefix))
#         ]
#     ]

#     return [
#         [account, user_to_json(user)]
#         for [account, user] in game
#     ]


# def sync_json(prefix: str) -> None:
#     for [account, j] in pickle_to_json(prefix):
#         user_name = account.split('.')[-1]
#         new_prefix = '.'.join(account.split('.')[0:-1]) + '.json'
#         new_key = '{}.{}'.format(new_prefix, user_name)
#         redis.set(
#             new_key,
#             j
#         )


# redix key prefix -> List[User]
def hydrate_json(prefix: str) -> List[User]:
    return [
        User.from_json(redis.get(account))  # type: ignore
        for account in redis.keys('{}.*'.format(prefix))
    ]


# sync_json('cryptoTrader.test')
print(
    hydrate_json('cryptoTrader.test.json')
)

users = hydrate_json('cryptoTrader.test.json')

jsons = [
    user.to_json()  # type: ignore
    for user in users
]

print(jsons)

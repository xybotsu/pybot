from dataclasses import dataclass
from typing import List
from requests import get
from json import loads, JSONDecoder
from .FastJsonDecoder import FastJsonDecoder


@dataclass(frozen=True)
class Listing:
    id: int
    name: str
    symbol: str
    website_slug: str


@dataclass(frozen=True)
class ListingMeta:
    timestamp: int
    num_cryptocurrencies: int
    error: str


@dataclass(frozen=True)
class Listings:
    data: List[Listing]
    metadata: ListingMeta


class ListingsDecoder(FastJsonDecoder):
    def jsonToClass(self):
        return {
            ('id', 'name', 'symbol', 'website_slug'): Listing,
            ('timestamp', 'num_cryptocurrencies', 'error'): ListingMeta,
            ('data', 'metadata'): Listings
        }


URL = 'https://api.coinmarketcap.com/v2/{resource}/'


def getListings() -> Listings:
    resp = get(URL.format(resource='listings'))
    return loads(resp.text, cls=ListingsDecoder)


def mono(str):
    return "```{str}```".format(str=str)


def onCryptoListings(slack, cmd):
    channel, thread = cmd.channel, cmd.thread
    str = ", ".join(list(map(lambda d: d.symbol, getListings().data)))
    slack.rtm_send_message(channel, mono(str), thread)

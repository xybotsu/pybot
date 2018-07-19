from requests import get
from json import loads, JSONDecoder
from .models import Listings, ListingsDecoder, Tickers, TickersDecoder
from typing import Dict

URL = 'https://api.coinmarketcap.com/v2/{resource}'


def getListings() -> Listings:
    resp = get(URL.format(resource='listings'))
    return loads(resp.text, cls=ListingsDecoder)


def getTickers() -> Tickers:
    resp = get(URL.format(
        resource='ticker/?limit=100&sort=rank&structure=array')
    )
    return loads(resp.text, cls=TickersDecoder)


def getPrices() -> Dict[str, float]:
    return {
        ticker.symbol.lower(): ticker.quotes['USD'].price
        for ticker in getTickers().data
    }

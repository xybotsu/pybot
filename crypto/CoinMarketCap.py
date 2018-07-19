from requests import get, Response
from json import loads, JSONDecoder
from .models import Listings, ListingsDecoder, Ticker, Tickers, TickersDecoder
from typing import Dict, List, Tuple
import time


def current_time_ms() -> int:
    return int(round(time.time() * 1000))


class CachedGet:

    def __init__(self, cache_time_ms: int) -> None:
        self.cache: Dict[str, Tuple[Response, int]] = {}
        self.cache_time_ms = cache_time_ms
        self.total_api_calls = 0

    def _isOld(self, t: int) -> bool:
        return current_time_ms() - t > self.cache_time_ms

    def _needsCacheRefresh(self, url: str) -> bool:
        # True if url not in cache OR url is stale in cache

        isNotInCache = url not in self.cache.keys()
        isStaleInCache = (
            url in self.cache.keys() and
            self._isOld(self.cache[url][1])
        )

        return isNotInCache or isStaleInCache

    def get(self, url: str) -> Response:
        if self._needsCacheRefresh(url):
            print("cache stale; fetching {url}".format(url=url))
            resp = get(url)
            self.total_api_calls = self.total_api_calls + 1
            print("{n} api calls made".format(n=self.total_api_calls))
            self.cache[url] = (resp, current_time_ms())
            return resp
        else:
            print("cache hit! already have data for {url}".format(url=url))
            return self.cache[url][0]


class CoinMarketCapApi:

    URL = 'https://api.coinmarketcap.com/v2/{resource}'
    REFRESH_TIME_MS = 5 * 60 * 1000  # data refreshes every 5 min

    def __init__(self) -> None:
        self.getter = CachedGet(CoinMarketCapApi.REFRESH_TIME_MS)

    def getListings(self) -> Listings:
        resp = self.getter.get(
            CoinMarketCapApi.URL.format(resource='listings')
        )
        return loads(resp.text, cls=ListingsDecoder)

    def getTickers(self) -> Tickers:
        resp = self.getter.get(
            CoinMarketCapApi.URL.format(
                resource='ticker/?limit=100&sort=rank&structure=array'
            )
        )
        return loads(resp.text, cls=TickersDecoder)

    def getPrices(self) -> Dict[str, float]:
        return {
            ticker.symbol.lower(): ticker.quotes['USD'].price
            for ticker in self.getTickers().data
        }

    def getTopNTickersAndPrices(self, n: int) -> List[Ticker]:
        tickers = self.getTickers().data
        sortedTickers = sorted(
            tickers,
            key=lambda t: t.rank
        )[0:n]
        return sortedTickers

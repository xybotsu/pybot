from requests import request, Response
from json import loads, JSONDecoder
from .models import Listings, Listing, ListingsDecoder
from typing import Dict, List, Tuple
import os
import time

CMC_API_KEY = os.getenv("CMC_API_KEY", "")
if CMC_API_KEY == "":
    raise TypeError(
        "\n[ERROR] please add CMC_API_KEY (CoinMarketCap API Key) to your ENV"
    )


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
        isStaleInCache = url in self.cache.keys() and self._isOld(self.cache[url][1])

        return isNotInCache or isStaleInCache

    def request(
        self, method: str, url: str, headers: Dict[str, str], params: Dict[str, str]
    ) -> Response:
        if self._needsCacheRefresh(url):
            print("cache stale; fetching {url}".format(url=url))
            resp = request(method, url, headers=headers, params=params)
            self.total_api_calls = self.total_api_calls + 1
            print("{n} api calls made".format(n=self.total_api_calls))
            self.cache[url] = (resp, current_time_ms())
            return resp
        else:
            return self.cache[url][0]


class CoinMarketCapApi:

    URL = "https://pro-api.coinmarketcap.com/v1/{resource}"
    REFRESH_TIME_MS = 1 * 60 * 1000  # data refreshes every 1 min

    def __init__(self) -> None:
        self.getter = CachedGet(CoinMarketCapApi.REFRESH_TIME_MS)

    def getListings(self) -> Listings:
        resp = self.getter.request(
            "get",
            CoinMarketCapApi.URL.format(resource="cryptocurrency/listings/latest"),
            {
                "X-CMC_PRO_API_KEY": CMC_API_KEY,
            },
            {"limit": "200", "cryptocurrency_type": "all", "sort": "market_cap", "sort_dir": "desc"},
        )
        return loads(resp.text, cls=ListingsDecoder)

    def getPrices(self) -> Dict[str, float]:
        listings = self.getListings().data
        print(listings[0])
        return {
            listing.symbol.lower(): listing.quote["USD"]["price"]
            for listing in listings
        }

    def getTopNListings(self, n: int) -> List[Listing]:
        listings = self.getListings().data
        sortedListings = sorted(listings, key=lambda l: l.cmc_rank)[0:n]
        return sortedListings

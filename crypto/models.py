from dataclasses import dataclass
from typing import Dict, List
from .decoders import FastJsonDecoder

# -- CoinMarketCap Listings API -- #
# https://pro-api.coinmarketcap.com/v1/cryptocurrency/listings/latest


@dataclass(frozen=True)
class Quote:
    price: float
    volume_24h: float
    percent_change_1h: float
    percent_change_24h: float
    percent_change_7d: float
    market_cap: float
    last_updated: str


@dataclass(frozen=True)
class Listing:
    id: int
    name: str
    symbol: str
    slug: str
    circulating_supply: int
    total_supply: int
    max_supply: int
    date_added: str
    num_market_pairs: int
    tags: List[str]
    platform: str
    cmc_rank: int
    last_updated: str
    quote: Dict[str, Quote]


@dataclass(frozen=True)
class Status:
    timestamp: str
    error_code: int
    error_message: str
    elapsed: int
    credit_count: int


@dataclass(frozen=True)
class Listings:
    status: Status
    data: List[Listing]


class ListingsDecoder(FastJsonDecoder):
    def jsonToClass(self):
        return {
            (
                "timestamp",
                "error_code",
                "error_message",
                "elapsed",
                "credit_count",
            ): Status,
            (
                "id",
                "name",
                "symbol",
                "slug",
                "circulating_supply",
                "total_supply",
                "max_supply",
                "date_added",
                "num_market_pairs",
                "tags",
                "platform",
                "cmc_rank",
                "last_updated",
                "quote",
            ): Listing,
            (
                "price",
                "volume_24h",
                "percent_change_1h",
                "percent_change_24h",
                "percent_change_7d",
                "market_cap",
                "last_updated",
            ): Quote,
            ("status", "data"): Listings,
        }

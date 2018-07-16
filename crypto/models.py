from dataclasses import dataclass
from typing import Dict, List
from .decoders import FastJsonDecoder

# -- Listing -- #


@dataclass(frozen=True)
class Listing:
    id: int
    name: str
    symbol: str
    website_slug: str


@dataclass(frozen=True)
class Meta:
    timestamp: int
    num_cryptocurrencies: int
    error: str


@dataclass(frozen=True)
class Listings:
    data: List[Listing]
    metadata: Meta


class ListingsDecoder(FastJsonDecoder):
    def jsonToClass(self):
        return {
            ('id', 'name', 'symbol', 'website_slug'): Listing,
            ('timestamp', 'num_cryptocurrencies', 'error'): Meta,
            ('data', 'metadata'): Listings
        }

# -- Ticker -- #


@dataclass(frozen=True)
class Quote:
    price: float
    volume_24h: float
    market_cap: float
    percent_change_1h: float
    percent_change_24h: float
    percent_change_7d: float


@dataclass(frozen=True)
class Ticker:
    id: int
    name: str
    symbol: str
    website_slug: str
    rank: int
    circulating_supply: float
    total_supply: float
    max_supply: float
    quotes: Dict[str, Quote]
    last_updated: int


@dataclass(frozen=True)
class Tickers:
    data: List[Ticker]
    metadata: Meta


class TickersDecoder(FastJsonDecoder):
    def jsonToClass(self):
        return {
            ('id', 'name', 'symbol', 'website_slug', 'rank',
                'circulating_supply', 'total_supply', 'max_supply',
                'quotes', 'last_updated'): Ticker,
            ('timestamp', 'num_cryptocurrencies', 'error'): Meta,
            ('data', 'metadata'): Tickers,
            ('price', 'volume_24h', 'market_cap', 'percent_change_1h',
                'percent_change_24h', 'percent_change_7d'): Quote
        }

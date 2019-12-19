from dataclasses import dataclass, field
from dataclasses_json import dataclass_json
from typing import Dict, List, Tuple, Union
from .CoinMarketCap import CachedGet, CoinMarketCapApi
from collections import defaultdict
from redis import StrictRedis
from prettytable import PrettyTable
from imagemaker.makePng import getCryptoLeaderboardPng, getCryptoTopPng
import json


@dataclass_json
@dataclass
class Condition:
    coin: str
    condition: str
    price: float


@dataclass_json
@dataclass
class Alert:
    pass


@dataclass_json
@dataclass
class Buy:
    coin: str
    qty: float


@dataclass_json
@dataclass
class Sell:
    coin: str
    qty: float


@dataclass_json
@dataclass
class If:
    id: int
    condition: Condition
    action: Union[Alert, Buy, Sell]


@dataclass_json
@dataclass
class User:
    user_name: str
    balance: float
    portfolio: Dict[str, float]
    ifs: List[If] = field(default_factory=list)

    def display_portfolio(self) -> Dict[str, float]:
        # don't include entries with 0 value
        return {
            k: v
            for k, v in self.portfolio.items()
            if v != 0.0
        }

    def value(self, prices: Dict[str, float]) -> float:
        sum = 0.0
        for ticker, quantity in self.portfolio.items():
            sum = sum + prices.get(ticker, 0) * quantity
        return sum


class CryptoTrader:

    INITIAL_POT_SIZE = 100000

    def __init__(self, db: StrictRedis, group: str) -> None:
        self.db = db
        self.group = group
        self.api = CoinMarketCapApi()
        pass

    def buy(self, user_name: str, ticker: str, quantity: float) -> None:
        user = self._getUser(user_name)
        prices = self.api.getPrices()
        ticker = ticker.lower()

        if (ticker not in prices):
            raise InvalidCoinError(
                "Price missing for {ticker}. Try a different coin."
                .format(ticker=ticker)
            )

        purchasePrice = prices[ticker] * quantity
        if (user.balance > purchasePrice):
            user.portfolio[ticker] = user.portfolio.get(
                ticker
            ) or 0  # initialize if needed
            user.portfolio[ticker] += quantity
            user.balance = user.balance - purchasePrice
            self._setUser(user)
        else:
            raise InsufficientFundsError(
                "{user_name} is out of dough!"
                .format(user_name=user_name)
            )

    def sell(self, user_name: str, ticker: str, quantity: float) -> None:
        user = self._getUser(user_name)
        prices = self.api.getPrices()
        ticker = ticker.lower()

        if (
            user.portfolio.get(ticker) and
            user.portfolio[ticker] >= quantity
        ):
            sellPrice = prices[ticker] * quantity
            user.portfolio[ticker] -= quantity
            user.balance += sellPrice
            self._setUser(user)
        else:
            raise InsufficientCoinsError(
                "{user_name} don't have {coin} coins to sell!"
                .format(user_name=user_name, coin=ticker)
            )

    def getIfs(self, user_name: str) -> List[If]:
        user = self._getUser(user_name)
        return user.ifs

    def deleteIf(self, user_name: str, id: int) -> None:
        # TODO: implement
        return

    def setAlertIf(
        self,
        user_name: str,
        coin: str,
        comparator: str,
        amount: float
    ) -> None:
        # TODO: implement
        return

    def setBuyIf(
        self,
        user_name: str,
        coin: str,
        comparator: str,
        amount: float,
        buyCoin: str,
        buyQty: str
    ) -> None:
        # TODO: implement
        return

    def setSellIf(
        self,
        user_name: str,
        coin: str,
        comparator: str,
        amount: float,
        sellCoin: str,
        sellQty: str
    ) -> None:
        # TODO: implement
        return

    def _key(self, user_name: str) -> str:
        return "cryptoTrader.{group}.json.{user_name}".format(
            group=self.group,
            user_name=user_name
        )

    def _getUser(self, user_name: str) -> User:
        if not self.db.get(self._key(user_name)):
            self._setUser(
                User(
                    user_name,
                    CryptoTrader.INITIAL_POT_SIZE,
                    {}
                )
            )
        return User.from_json(  # type: ignore
            self.db.get(
                self._key(user_name)
            )
        )

    def _getAllUsers(self) -> List[User]:
        userKeys = self.db.keys("cryptoTrader.{g}.json.*".format(g=self.group))
        if not userKeys:
            return []
        return [
            User.from_json(u)  # type: ignore
            for u in self.db.mget(userKeys)
        ]

    def _setUser(self, user: User) -> None:
        self.db.set(self._key(user.user_name), user.to_json())  # type: ignore

    def create_user(self, user_name):
        if not self.db.get(self._key(user_name)):
            self._setUser(
                User(
                    user_name,
                    100000,
                    {}
                )
            )

    def delete_user(self, user_name: str) -> None:
        if self.db.get(self._key(user_name)):
            self.db.delete(self._key(user_name))

    def status(self, user_name: str) -> str:
        user = self._getUser(user_name)
        return (
            "```User {user_name} has ${balance} to spend.\n" +
            "Coins owned: {portfolio}\n" +
            "Portfolio value is ${value}```"
        ).format(
            user_name=user.user_name,
            balance=user.balance,
            portfolio=user.display_portfolio(),
            value=user.value(self.api.getPrices())
        )

    def topCoins(self, n: int) -> str:
        topListings = self.api.getTopNListings(n)

        rows = []
        for listing in topListings:
            rows.append(
                (
                    listing.symbol,
                    _format_money(listing.quote['USD'].price),
                    _format_suffix(listing.quote['USD'].volume_24h),
                    _format_suffix(listing.quote['USD'].market_cap),
                    listing.quote['USD'].percent_change_1h,
                    listing.quote['USD'].percent_change_24h,
                    listing.quote['USD'].percent_change_7d
                )
            )

        return getCryptoTopPng(rows)

    def leaderboard(self):
        users = self._getAllUsers()

        if not users:
            return 'No leaderboard created yet. `crypto help` to start.'

        prices = self.api.getPrices()

        # sort users by total $, descending
        sortedUsers = sorted(
            users,
            key=lambda u: u.balance + u.value(prices),
            reverse=True
        )

        rows = []
        for user in sortedUsers:
            rows.append(
                (
                    user.user_name,
                    user.display_portfolio(),
                    _format_money(user.value(prices)),
                    _format_money(user.balance),
                    _format_money(user.balance + user.value(prices)),
                    (
                        (user.balance + user.value(prices)) -
                        CryptoTrader.INITIAL_POT_SIZE

                    )
                )
            )

        return getCryptoLeaderboardPng(rows)


class Error(Exception):
    pass


class InsufficientFundsError(Error):
    pass


class InsufficientCoinsError(Error):
    pass


class InvalidCoinError(Error):
    pass


def _format_money(n: float) -> str:
    return "{0:.1f}".format(n)


def _format_pct(n: float) -> str:
    return "{0:.1f}".format(n)


def _format_suffix(num):
    magnitude = 0
    while abs(num) >= 1000:
        magnitude += 1
        num /= 1000.0
    # add more suffixes if you need them
    return '%.2f%s' % (num, ['', 'K', 'M', 'B', 'T', 'P'][magnitude])

from dataclasses import dataclass
import pickle
from typing import Dict, List, Tuple, Union
from .CoinMarketCap import CachedGet, CoinMarketCapApi
from collections import defaultdict
from redis import StrictRedis
from prettytable import PrettyTable
from imagemaker.makePng import getCryptoLeaderboardPng, getCryptoTopPng

Stop = Tuple[str, float, float]  # [ticker, qty, stopPrice]

@dataclass
class User:
    user_name: str
    balance: float
    portfolio: Dict[str, float]  # ticker, qty
    _stops: Dict[int, Stop]  # stopID, Stop

    def getStop(self, stopID: int) -> Stop:
        try:
            self._stops
        except:
            self._stops = {}
        return self._stops[stopID]

    def setStop(self, stopID: int, stop: Stop) -> None:
        try:
            self._stops
        except:
            self._stops = {}
        self._stops[stopID] = stop

    def delStop(self, stopID: int) -> None:
        try:
            self._stops
        except:
            self._stops = {}
        del self._stops[stopID]

    def getAllStops(self) -> Dict[int, Stop]:
        try:
            self._stops
        except:
            self._stops = {}
        return self._stops

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

    def getStops(self, user_name: str) -> Dict[int, Stop]:
        user = self._getUser(user_name)
        return user.getAllStops()

    def nextStopID(self, user: User) -> int:
        if(len(user.getAllStops()) == 0):
            return 0
        prev = -1
        for id in user.getAllStops().keys():
            if(id != prev+1):
                return prev+1
            prev = int(id)
        return prev+1

    def addStop(self, user_name: str, stop: Stop) -> Union[Error, User]:
        user = self._getUser(user_name)
        (ticker, quantity, price) = stop
        prices = self.api.getPrices()
        ticker = ticker.lower()

        if (ticker not in prices):
            return InvalidCoinError(
                "Price missing for {ticker}. Try a different coin."
                .format(ticker=ticker)
            )
        if (user.portfolio.get(ticker) and user.portfolio[ticker] < quantity):
            return InsufficientCoinsError(
                "{user_name} don't have {coin} coins to sell!"
                .format(user_name=user.user_name, coin=ticker)
            )
        stopID = self.nextStopID(user)
        user.setStop(stopID, (ticker, quantity, price))
        return user

    def updateStop(self, user_name: str, stopID: int, qty: float, price: float) -> Union[Error, User]:
        user = self._getUser(user_name)
        prices = self.api.getPrices()
        stop = user.getStop(stopID)
        ticker = stop[0].lower()

        if (
            user.portfolio.get(ticker) and
            user.portfolio[ticker] >= qty
        ):
            user.setStop(stopID, (ticker, qty, price))
            return user
        else:
            return InsufficientCoinsError(
                "{user_name} don't have {coin} coins to sell!"
                .format(user_name=user.user_name, coin=ticker)
            )

    def deleteStop(self, user_name: str, stopID: int) -> Union[Error, User]:
        user = self._getUser(user_name)
        user.delStop(stopID)
        return user

    def checkStops(self) -> List[Tuple[str, int, str, float, float]]:
        sales: List = []
        for user in self._getAllUsers():
            user_name = user.user_name
            for stopID, (ticker, qty, stopPrice) in user.getAllStops().items():
                price = self.api.getPrices().get(ticker)
                if price is None:
                    raise Error("price not found for {}".format(ticker))
                elif stopPrice <= price:
                    user.delStop(stopID)
                    self.sell(user_name, ticker, qty)
                    sales.append((user_name, stopID, ticker, qty, stopPrice))
        return sales

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

    def _key(self, user_name: str) -> str:
        return "cryptoTrader.{group}.{user_name}".format(
            group=self.group,
            user_name=user_name
        )

    def _getUser(self, user_name: str) -> User:
        if not self.db.get(self._key(user_name)):
            self._setUser(
                User(
                    user_name,
                    CryptoTrader.INITIAL_POT_SIZE,
                    {},
                    {}
                )
            )
        return pickle.loads(
            self.db.get(
                self._key(user_name)
            )
        )

    def _getAllUsers(self) -> List[User]:
        userKeys = self.db.keys("cryptoTrader.{g}.*".format(g=self.group))
        if not userKeys:
            return []
        return [
            pickle.loads(u)
            for u in self.db.mget(userKeys)
        ]

    def _setUser(self, user: User) -> None:
        user = self._validateUser(user)
        self.db.set(self._key(user.user_name), pickle.dumps(user))

    def _validateUser(self, user: User) -> User:
        for stopID, (ticker, qty, stopPrice) in user.getAllStops().items():
            if qty > user.portfolio[ticker]:
                if user.portfolio[ticker] == 0:
                    user.delStop(stopID)
                else:
                    res = self.updateStop(
                        user.user_name,
                        stopID,
                        user.portfolio[ticker],
                        stopPrice
                    )
                    if (isinstance(res, Error)):
                        print(Error)
                    else:
                        user = res
        return user

    def create_user(self, user_name: str) -> None:
        if not self.db.get(self._key(user_name)):
            self._setUser(
                User(
                    user_name,
                    100000,
                    {},
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

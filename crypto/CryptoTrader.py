from dataclasses import dataclass
import pickle
from typing import Dict, List
from .CoinMarketCap import CachedGet, CoinMarketCapApi
from collections import defaultdict
from redis import StrictRedis
from prettytable import PrettyTable


@dataclass
class User:
    user_name: str
    balance: float
    portfolio: Dict[str, float]

    def display_portfolio(self) -> Dict[str, float]:
        # don't include entries with 0 value
        return {
            k: v
            for k, v in self.portfolio.items()
            if v != 0.0
        }

    def value(self, prices) -> float:
        sum = 0
        for ticker, quantity in self.portfolio.items():
            sum = sum + prices.get(ticker) * quantity
        return sum


class CryptoTrader:

    INITIAL_POT_SIZE = 100000

    def __init__(self, db: StrictRedis, group) -> None:
        self.db = db
        self.group = group
        self.api = CoinMarketCapApi()
        pass

    def buy(self, user_name: str, ticker: str, quantity: float) -> None:
        user = self._getUser(user_name)
        prices = self.api.getPrices()
        ticker = ticker.lower()

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
        self.db.set(self._key(user.user_name), pickle.dumps(user))

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

    def leaderboard(self) -> str:
        users = self._getAllUsers()

        if not users:
            return 'No leaderboard created yet. `crypto help` to start.'

        prices = self.api.getPrices()

        table = PrettyTable(
            ['Player', 'Coins', 'Coins $', 'Cash $', 'Total'])
        for user in users:
            table.add_row([
                user.user_name,
                user.display_portfolio(),
                _format_money(user.value(prices)),
                _format_money(user.balance),
                _format_money(user.balance + user.value(prices))
            ])
        return table.get_string(
            sortby='Total',
            reversesort=True
        )


class Error(Exception):
    pass


class InsufficientFundsError(Error):
    pass


class InsufficientCoinsError(Error):
    pass


def _format_money(n):
    return "${0:.2f}".format(n)

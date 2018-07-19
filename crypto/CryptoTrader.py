from dataclasses import dataclass
import pickle
from typing import Dict, List
from .CoinMarketCap import getPrices
from collections import defaultdict

'''
db.get(key: str)
db.set(key: str, val: Any)

'''


class CryptoTrader:

    INITIAL_POT_SIZE = 100000

    def __init__(self, db, group):
        self.db = db
        self.group = group
        pass

    def buy(self, user_name, ticker, quantity):
        user = self._getUser(user_name)
        prices = getPrices()
        ticker = ticker.lower()

        purchasePrice = prices.get(ticker) * quantity
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

    def sell(self, user_name, ticker, quantity):
        user = self._getUser(user_name)
        prices = getPrices()
        ticker = ticker.lower()

        if (
            user.portfolio.get(ticker) and
            user.portfolio.get(ticker) >= quantity
        ):
            sellPrice = prices.get(ticker) * quantity
            user.portfolio[ticker] -= quantity
            user.balance += sellPrice
            self._setUser(user)
        else:
            raise InsufficientCoinsError(
                "{user_name} don't have {coin} coins to sell!"
                .format(user_name=user_name, coin=ticker)
            )

    def _key(self, user_name):
        return "cryptoTrader.{group}.{user_name}".format(
            group=self.group,
            user_name=user_name
        )

    def _getUser(self, user_name):
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

    def _setUser(self, user):
        self.db.set(self._key(user.user_name), pickle.dumps(user))

    def status(self, user_name):
        user = self._getUser(user_name)
        print(user)
        return (
            "```User {user_name} has ${balance} to spend.\n" +
            "Coins owned: {portfolio}\n" +
            "Portfolio value is ${value}```"
        ).format(
            user_name=user.user_name,
            balance=user.balance,
            portfolio=user.display_portfolio(),
            value=user.value(getPrices())
        )


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


class Error(Exception):
    pass


class InsufficientFundsError(Error):
    pass


class InsufficientCoinsError(Error):
    pass

from dataclasses import dataclass, field
from dataclasses_json import dataclass_json
from typing import Dict, List, Tuple, Union
from typing_extensions import Literal
from .CoinMarketCap import CachedGet, CoinMarketCapApi
from collections import defaultdict
from redis import StrictRedis
from prettytable import PrettyTable
from imagemaker.makePng import getCryptoLeaderboardPng, getCryptoTopPng
import json, re, math


@dataclass_json
@dataclass
class Condition:
    coin: str
    comparator: str  # > or <
    price: float

    def render(self) -> str:
        if self.comparator == "&gt;":
            comp = ">"
        elif self.comparator == "&lt;":
            comp = "<"
        return "{} {} {}".format(self.coin, comp, self.price)


@dataclass_json
@dataclass
class Alert:
    msg: str
    type: Literal["alert"] = "alert"


@dataclass_json
@dataclass
class Buy:
    coin: str
    qty: str
    type: Literal["buy"] = "buy"


@dataclass_json
@dataclass
class Sell:
    coin: str
    qty: str
    type: Literal["sell"] = "sell"


@dataclass_json
@dataclass
class If:
    id: int
    condition: Condition
    action: Union[Alert, Buy, Sell]

    def meets_condition(self, prices: Dict[str, float]) -> bool:
        if self.condition.comparator == "&gt;":
            return prices[self.condition.coin] > self.condition.price
        elif self.condition.comparator == "&lt;":
            return prices[self.condition.coin] < self.condition.price
        else:
            raise InvalidConditionError(
                "We only support a > b or a < b conditions at this time."
            )

    def render(self) -> str:
        if self.action["type"] == "alert":
            return "[id {}] if {} {} {} alert".format(
                self.id,
                self.condition.coin,
                self.condition.comparator,
                self.condition.price,
            )
        else:
            return "[id {}] if {} {} {} {} {} {}".format(
                self.id,
                self.condition.coin,
                self.condition.comparator,
                self.condition.price,
                self.action["type"],
                self.action["coin"],
                self.action["qty"],
            )


@dataclass_json
@dataclass
class User:
    user_name: str
    balance: float
    portfolio: Dict[str, float]
    ifs: List[If] = field(default_factory=list)

    def display_portfolio(self) -> Dict[str, float]:
        # don't include entries with small value
        return {k: round(v,max(0,min(6,6-math.floor(math.log(v,10))))) for k, v in self.portfolio.items() if v >= 1e-6}

    def value(self, prices: Dict[str, float]) -> float:
        sum = 0.0
        for ticker, quantity in self.portfolio.items():
            sum = sum + prices.get(ticker, 0) * quantity
        return sum

    def get_next_if_id(self) -> int:
        if len(self.ifs) == 0:
            return 1
        else:
            return max([i.id for i in self.ifs]) + 1


class CryptoTrader:

    INITIAL_POT_SIZE = 100000

    def __init__(self, db: StrictRedis, group: str) -> None:
        self.db = db
        self.group = group
        self.api = CoinMarketCapApi()

    def buy(self, user_name: str, ticker: str, quantity: str) -> None:
        user = self._getUser(user_name)
        prices = self.api.getPrices()
        ticker = ticker.lower()
        qty = 0.0

        if ticker not in prices:
            raise InvalidCoinError(
                "Price missing for {ticker}. Try a different coin.".format(
                    ticker=ticker
                )
            )

        if quantity == 'all' or quantity == 'max': quantity = '100%'
        elif quantity == 'half': quantity = '50%'
        
        if re.match('^\d+\.?\d*%$',quantity):
            qty = user.balance/prices[ticker] * max(0,min(100,float(quantity.strip('%'))/100))
        else:
            try:
                qty = float(quantity)
            except:
                raise InvalidBuyQuantityError(
                    "Either buy a numeric amount of coin, or specify 'max', 'all', 'half', or some percentage."
                )
        if qty <= 0:
            raise InvalidBuyQuantityError("Buy quantity must be greater than zero.")

        purchasePrice = prices[ticker] * qty
        if user.balance >= purchasePrice:
            user.portfolio[ticker] = (
                user.portfolio.get(ticker) or 0
            )  # initialize if needed
            user.portfolio[ticker] += qty
            user.balance = user.balance - purchasePrice
            self._setUser(user)
        else:
            raise InsufficientFundsError(
                "{user_name} is out of dough!".format(user_name=user_name)
            )

    def sell(self, user_name: str, ticker: str, quantity: str) -> None:
        user = self._getUser(user_name)
        prices = self.api.getPrices()
        ticker = ticker.lower()
        qty = 0.0

        if quantity == 'all' or quantity == 'max': quantity = '100%'
        elif quantity == 'half': quantity = '50%'

        if re.match('^\d+\.?\d*%$',quantity):
            qty = user.portfolio[ticker] * max(0,min(100,float(quantity.strip('%'))/100))
        else:
            try:
                qty = float(quantity)
            except:
                raise InvalidSellQuantityError(
                    "Either sell a numeric amount of coin, or specify 'max', 'all', 'half', or some percentage."
                )
        if qty <= 0:
            raise InvalidSellQuantityError("Sell quantity must be greater than zero.")

        if user.portfolio.get(ticker) and user.portfolio[ticker] >= qty:
            sellPrice = prices[ticker] * qty
            user.portfolio[ticker] -= qty
            user.balance += sellPrice
            self._setUser(user)
        else:
            raise InsufficientCoinsError(
                "{user_name} don't have {coin} coins to sell!".format(
                    user_name=user_name, coin=ticker
                )
            )

    def deleteIf(self, user_name: str, id: int) -> None:
        user = self._getUser(user_name)
        user.ifs = [i for i in user.ifs if i.id != id]
        self._setUser(user)

    def setAlertIf(
        self, user_name: str, coin: str, comparator: str, amount: float
    ) -> None:
        user = self._getUser(user_name)
        prices = self.api.getPrices()

        if coin not in prices:
            raise InvalidCoinError(
                "Price missing for {coin}. Try a different coin.".format(coin=coin)
            )

        if coin not in prices:
            raise InvalidCoinError(
                "Price missing for {coin}. Try a different coin.".format(coin=coin)
            )

        price = prices[coin]

        # coin > amount
        if comparator == "&gt;" and price > amount:
            raise InvalidAlertError(
                "Invalid alert. Price of {} is already > {}".format(coin, amount)
            )
        elif comparator == "&lt;" and price < amount:
            raise InvalidAlertError(
                "Invalid alert. Price of {} is already < {}".format(coin, amount)
            )
        else:
            id = user.get_next_if_id()
            user.ifs.append(
                If(
                    id,
                    Condition(coin, comparator, amount),
                    Alert(
                        msg="Alert! The price of {} is {} {}.".format(
                            coin, comparator, amount
                        )
                    ),
                )
            )
            self._setUser(user)

    def setBuyIf(
        self,
        user_name: str,
        coin: str,
        comparator: str,
        amount: float,
        buyCoin: str,
        buyQty: str,
    ) -> None:
        user = self._getUser(user_name)
        prices = self.api.getPrices()

        if coin not in prices:
            raise InvalidCoinError(
                "Price missing for {coin}. Try a different coin.".format(coin=coin)
            )

        if buyCoin not in prices:
            raise InvalidCoinError(
                "Price missing for {buyCoin}. Try a different coin.".format(
                    buyCoin=buyCoin
                )
            )

        if buyQty == 'all' or buyQty == 'max': buyQty = '100%'
        elif buyQty == 'half': buyQty = '50%'
        
        if not re.match('^\d+\.?\d*%$',buyQty):
            try:
                if float(buyQty) <= 0: raise InvalidBuyQuantityError("Buy quantity must be greater than zero.")
            except:
                raise InvalidBuyQuantityError(
                    "Either buy a numeric amount of coin, or specify 'max', 'all', 'half', or some percentage."
                )

        price = prices[coin]

        # coin > amount
        if comparator == "&gt;" and price > amount:
            raise InvalidAlertError(
                "Invalid buy. Price of {} is already > {}".format(coin, amount)
            )
        elif comparator == "&lt;" and price < amount:
            raise InvalidAlertError(
                "Invalid buy. Price of {} is already < {}".format(coin, amount)
            )
        else:
            id = user.get_next_if_id()
            user.ifs.append(
                If(
                    id,
                    Condition(coin, comparator, amount),
                    Buy(coin=buyCoin, qty=buyQty),  # either float or percentage
                )
            )
            self._setUser(user)

    def setSellIf(
        self,
        user_name: str,
        coin: str,
        comparator: str,
        amount: float,
        sellCoin: str,
        sellQty: str,
    ) -> None:
        user = self._getUser(user_name)
        prices = self.api.getPrices()

        if coin not in prices:
            raise InvalidCoinError(
                "Price missing for {coin}. Try a different coin.".format(coin=coin)
            )

        if sellCoin not in prices:
            raise InvalidCoinError(
                "Price missing for {sellCoin}. Try a different coin.".format(
                    sellCoin=sellCoin
                )
            )

        if sellQty == 'all' or sellQty == 'max': sellQty = '100%'
        elif sellQty == 'half': sellQty = '50%'
        
        if not re.match('^\d+\.?\d*%$',sellQty):
            try:
                if float(sellQty) <= 0: raise InvalidSellQuantityError("Sell quantity must be greater than zero.")
            except:
                raise InvalidSellQuantityError(
                    "Either sell a numeric amount of coin, or specify 'max', 'all', 'half', or some percentage."
                )

        price = prices[coin]

        # coin > amount
        if comparator == "&gt;" and price > amount:
            raise InvalidAlertError(
                "Invalid sell. Price of {} is already > {}".format(coin, amount)
            )
        elif comparator == "&lt;" and price < amount:
            raise InvalidAlertError(
                "Invalid sell. Price of {} is already < {}".format(coin, amount)
            )
        else:
            id = user.get_next_if_id()
            user.ifs.append(
                If(
                    id,
                    Condition(coin, comparator, amount),
                    Sell(coin=sellCoin, qty=sellQty),  # either float or some percentage
                )
            )
            self._setUser(user)

    def _key(self, user_name: str) -> str:
        return "cryptoTrader.{group}.json.{user_name}".format(
            group=self.group, user_name=user_name
        )

    def _getUser(self, user_name: str) -> User:
        if not self.db.get(self._key(user_name)):
            self._setUser(User(user_name, CryptoTrader.INITIAL_POT_SIZE, {}))
        return User.from_json(self.db.get(self._key(user_name)))  # type: ignore

    def getAllUsers(self) -> List[User]:
        userKeys = self.db.keys("cryptoTrader.{g}.json.*".format(g=self.group))
        if not userKeys:
            return []
        return [User.from_json(u) for u in self.db.mget(userKeys)]  # type: ignore

    def _setUser(self, user: User) -> None:
        self.db.set(self._key(user.user_name), user.to_json())  # type: ignore

    def create_user(self, user_name):
        if not self.db.get(self._key(user_name)):
            self._setUser(User(user_name, 100000, {}))

    def delete_user(self, user_name: str) -> None:
        if self.db.get(self._key(user_name)):
            self.db.delete(self._key(user_name))

    def status(self, user_name: str) -> str:
        user = self._getUser(user_name)
        return (
            "```User {user_name} has ${balance} to spend.\n"
            + "Coins owned: {portfolio}\n"
            + "Portfolio value is ${value}```"
        ).format(
            user_name=user.user_name,
            balance=user.balance,
            portfolio=user.display_portfolio(),
            value=user.value(self.api.getPrices()),
        )

    def topCoins(self, n: int) -> str:
        topListings = self.api.getTopNListings(n)

        rows = []
        for listing in topListings:
            rows.append(
                (
                    listing.symbol,
                    _format_money(listing.quote["USD"].price),
                    _format_suffix(listing.quote["USD"].volume_24h),
                    _format_suffix(listing.quote["USD"].market_cap),
                    listing.quote["USD"].percent_change_1h,
                    listing.quote["USD"].percent_change_24h,
                    listing.quote["USD"].percent_change_7d,
                )
            )

        return getCryptoTopPng(rows)

    def leaderboard(self):
        users = self.getAllUsers()

        if not users:
            return "No leaderboard created yet. `crypto help` to start."

        prices = self.api.getPrices()

        # sort users by total $, descending
        sortedUsers = sorted(
            users, key=lambda u: u.balance + u.value(prices), reverse=True
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
                        (user.balance + user.value(prices))
                        - CryptoTrader.INITIAL_POT_SIZE
                    ),
                )
            )

        return getCryptoLeaderboardPng(rows)


class Error(Exception):
    pass


class InvalidBuyQuantityError(Error):
    pass


class InvalidSellQuantityError(Error):
    pass


class InvalidAlertError(Error):
    pass


class InsufficientFundsError(Error):
    pass


class InsufficientCoinsError(Error):
    pass


class InvalidCoinError(Error):
    pass


class InvalidConditionError(Error):
    pass


def _format_money(n: float) -> str:
    return "{0:.2f}".format(round(n,2))


def _format_pct(n: float) -> str:
    return "{0:.2f}".format(n)


def _format_suffix(num):
    magnitude = 0
    while abs(num) >= 1000:
        magnitude += 1
        num /= 1000.0
    # add more suffixes if you need them
    return "%.2f%s" % (num, ["", "K", "M", "B", "T", "P"][magnitude])

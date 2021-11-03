from .CryptoTrader import (
    CryptoTrader,
    Alert,
    Buy,
    Sell,
    User,
    InsufficientFundsError,
    InsufficientCoinsError,
)
from bot.Bot import Bot, Command, SlackBot
from typing import Dict, List, Union, Optional
import threading


class CryptoBot(SlackBot):
    def __init__(self, token, bot: Bot, trader: CryptoTrader) -> None:
        super().__init__(token, bot, None)
        self.prices: Dict[str, float] = {}
        self.trader = trader
        self.lastLeaderboard: Union[str, None] = None
        self.lastTopCoins: Union[str, None] = None
        self.poll_and_execute_ifs()

    def poll_and_execute_ifs(self) -> None:
        # poll every 30 minutes
        # CoinMarketCap API limit is only 300 calls per day, so we need to limit the poll frequency here
        threading.Timer(60 * 30, self.poll_and_execute_ifs).start()

        # get all users
        self.old_prices = self.prices
        self.prices = self.trader.api.getPrices()
        if self.old_prices:
            msg = ''
            for ticker,price in self.prices.items():
                old_price = self.old_prices[ticker]
                change = 1 - price/old_price
                if change >= .1:
                    msg += "{} is UP {:.1%} in the last 30 min\n".format(ticker,change)
                elif change <= -.1:
                    msg += "{} is DOWN {:.1%} in the last 30 min\n".format(ticker,abs(change))
            msg = msg.strip()
            if msg != '':
                self.api_call(
                    "chat.postMessage",
                    channel="#crypto",
                    text=_mono(msg),
                    username=self.bot.name,
                    icon_emoji=self.bot.icon_emoji,
                )
        for user in self.trader.getAllUsers():
            self.execute_ifs(user, self.prices)

    def execute_ifs(self, user: User, prices: Dict[str, float]) -> None:
        idx = 0
        ifs = user.ifs
        while idx < len(ifs):
            try:
                i = ifs[idx]
                if not i.meets_condition(prices):
                    print(
                        "{} if id {} not met: {}".format(
                            user.user_name, i.id, i.condition.render()
                        )
                    )
                else:
                    print(
                        "{} if id {} triggered! {}".format(
                            user.user_name, i.id, i.condition.render()
                        )
                    )
                    if i.action["type"] == "alert":  # type: ignore
                        self.api_call(
                            "chat.postMessage",
                            channel="@{}".format(user.user_name),
                            text="{}".format(i.action["msg"]),  # type: ignore
                            username=self.bot.name,
                            icon_emoji=self.bot.icon_emoji,
                        )

                    elif i.action["type"] == "buy":  # type: ignore
                        coin = i.action["coin"]  # type: ignore
                        fromQty = "{0:.6g}".format(user.portfolio[coin] or 0)
                        buyQty = i.action["qty"]
                        fromUSD = "{0:.2f}".format(user.balance)
                        self.trader.buy(user.user_name, coin, buyQty)
                        db_user = self.trader._getUser(user.user_name)
                        user.portfolio = db_user.portfolio
                        user.balance = db_user.balance
                        toQty = "{0:.6g}".format(user.portfolio[coin] or 0)
                        toUSD = "{0:.2f}".format(user.balance)
                        msg = "{}\n[triggered] {} USD {} -> {}, {} {} -> {}".format(
                            i.render(),
                            user.user_name,
                            fromUSD,
                            toUSD,
                            coin,
                            fromQty,
                            toQty,
                        )
                        self.api_call(
                            "chat.postMessage",
                            channel="#crypto",
                            text=_mono(msg),
                            username=self.bot.name,
                            icon_emoji=self.bot.icon_emoji,
                        )
                        self._onLeaderboard("#crypto", None)
                    elif i.action["type"] == "sell":  # type: ignore
                        coin = i.action["coin"]  # type: ignore
                        fromQty = "{0:.6g}".format(user.portfolio[coin] or 0)
                        sellQty = i.action["qty"]  # type: ignore
                        fromUSD = "{0:.2f}".format(user.balance)
                        self.trader.sell(user.user_name, coin, sellQty)
                        db_user = self.trader._getUser(user.user_name)
                        user.portfolio = db_user.portfolio
                        user.balance = db_user.balance
                        toQty = "{0:.6g}".format(user.portfolio[coin] or 0)
                        toUSD = "{0:.2f}".format(user.balance)
                        msg = (
                            "{}\n[trade executed] {} USD {} -> {}, {} {} -> {}".format(
                                i.render(),
                                user.user_name,
                                fromUSD,
                                toUSD,
                                coin,
                                fromQty,
                                toQty,
                            )
                        )
                        self.api_call(
                            "chat.postMessage",
                            channel="#crypto",
                            text=_mono(msg),
                            username=self.bot.name,
                            icon_emoji=self.bot.icon_emoji,
                        )
                        self._onLeaderboard("#crypto", None)
                    # action succeeded, so remove it from ifs
                    del ifs[idx]
            except Exception as e:
                i = ifs[idx]
                self.api_call(
                    "chat.postMessage",
                    channel="@{}".format(user.user_name),
                    text="Execution of if failed. Condition: {}, Action: {}, Error: {}".format(
                        i.condition, i.action, str(e)
                    ),
                    username=self.bot.name,
                    icon_emoji=self.bot.icon_emoji,
                )
            idx = idx + 1
        self.trader._setUser(user)

    def deleteFileUploads(self, file):
        try:
            result = self.api_call("files.delete", file=file)
            print(result)
            self.fileUploads = []
        except:
            print("failed to delete files in deleteFileUploads()")

    def onHelp(self, cmd: Command):
        # crypto help
        channel, thread = cmd.channel, cmd.thread
        msg = "\n".join(
            [
                "crypto help",
                "crypto leaderboard",
                "crypto top",
                "crypto buy <ticker> <quantity>",
                "crypto sell <ticker> <quantity>",
                "crypto if <condition> <action>",
                "crypto price <ticker>",
                "crypto play",
                "crypto quit",
            ]
        )
        self.postMessage(channel, _mono(msg), thread)

    def onWhen(self, cmd: Command):
        # crypto when
        channel, thread = cmd.channel, cmd.thread

        msg = "no clue"
        if cmd.args[0] == "lambo":
            msg = ":racing_car:"
        elif cmd.args[0] == "moon":
            msg = ":full_moon_with_face:"
        elif cmd.args[0] == "hax":
            msg = "YOUR BALANCE = $420.69"

        self.postMessage(channel, msg, thread)

    def onPing(self, cmd: Command):
        channel, thread = cmd.channel, cmd.thread
        self.postMessage(channel, "pong!", thread)

    def onNewUser(self, cmd: Command):
        # crypto play
        user_name, args, channel, thread = (
            cmd.user_name,
            cmd.args,
            cmd.channel,
            cmd.thread,
        )
        # create user here...
        self.trader.create_user(user_name)
        self.onLeaderboard(cmd)

    def onUserQuit(self, cmd: Command):
        # crypto quit
        user_name, args, channel, thread = (
            cmd.user_name,
            cmd.args,
            cmd.channel,
            cmd.thread,
        )
        # delete user here...
        self.trader.delete_user(user_name)
        self.onLeaderboard(cmd)

    def displayIfs(self, user_name: str, channel: str, thread: str) -> None:
        ifs = self.trader._getUser(user_name).ifs
        if len(ifs) == 0:
            msg = "No ifs for {}!".format(user_name)
        else:
            msg = "\n".join([i.render() for i in ifs])
            msg = "Crypto ifs for {}\n{}".format(user_name, msg)
        self.postMessage(channel, _mono(msg), thread)

    # crypto if btc > 100 alert
    # crypto if btc > 100 sell btc max
    # crypto if btc > 100 sell btc 10
    # crypto if btc < 50 buy btc max
    # crypto if btc < 50 buy btc 10
    # crypto if
    # crypto if delete <id>

    def onIf(self, cmd: Command):
        user_name, args, channel, thread = (
            cmd.user_name,
            cmd.args,
            cmd.channel,
            cmd.thread,
        )

        print(args)

        # crypto if
        if len(args) == 0:
            self.displayIfs(user_name, channel, thread)

        # crypto if delete <id>
        elif args[0] == "delete":
            try:
                id = int(args[1])
                self.trader.deleteIf(user_name, id)
                self.displayIfs(user_name, channel, thread)
            except Exception as e:
                print(e)
                self.postMessage(
                    channel,
                    "`crypto delete <id>` is the format you're looking for.",
                    thread,
                )

        # crypto if btc > 100 alert
        # crypto if btc > 100 buy btc 100
        else:
            try:
                coin = args[0]
                comparator = args[1]
                amount = float(args[2])
                action = args[3]
                if action == "alert":
                    try:
                        self.trader.setAlertIf(user_name, coin, comparator, amount)
                        self.displayIfs(user_name, channel, thread)
                    except Exception as e:
                        self.postMessage(channel, _mono(str(e)), thread)
                        return
                elif action == "buy":
                    try:
                        buyCoin = args[4]
                        buyQty = args[5]
                        self.trader.setBuyIf(
                            user_name, coin, comparator, amount, buyCoin, buyQty
                        )
                        self.displayIfs(user_name, channel, thread)
                    except Exception as e:
                        self.postMessage(channel, _mono(str(e)), thread)
                        return
                elif action == "sell":
                    try:
                        sellCoin = args[4]
                        sellQty = args[5]
                        self.trader.setSellIf(
                            user_name, coin, comparator, amount, sellCoin, sellQty
                        )
                        self.displayIfs(user_name, channel, thread)
                    except Exception as e:
                        self.postMessage(channel, _mono(str(e)), thread)
                        return
            except Exception as e:
                print(e)
                msg = "\n".join(
                    [
                        "example commands",
                        "crypto if btc > 100 alert",
                        "crypto if btc > 100 sell btc max",
                        "crypto if btc > 100 sell btc 10",
                        "crypto if btc < 50 buy btc max",
                        "crypto if btc < 50 buy btc 10",
                        "crypto if",
                        "crypto if delete &lt;id&gt;",
                    ]
                )
                self.postMessage(channel, _mono(msg), thread)

    def onBuy(self, cmd: Command):
        # crypto buy eth 200
        user_name, args, channel, thread = (
            cmd.user_name,
            cmd.args,
            cmd.channel,
            cmd.thread,
        )
        try:
            ticker = args[0].lower().strip()
            quantity = args[1].lower().strip()
        except:
            self.postMessage(
                channel,
                "`crypto buy <ticker> <quantity>` is the format you're looking for.",
                thread,
            )
            return
        try:
            self.trader.buy(user_name, ticker, quantity)
            self.postMessage(
                channel,
                "{u} bought {t} x {q}".format(u=user_name, t=ticker, q=quantity),
                thread,
            )
            self.onLeaderboard(cmd)
        except InsufficientFundsError:
            self.postMessage(
                channel, "Insufficient funds. Try selling some coins for $!", thread
            )
        except:
            self.postMessage(channel, "Something went wrong.", thread)

    def onSell(self, cmd: Command):
        # crypto sell eth 200
        user_name, args, channel, thread = (
            cmd.user_name,
            cmd.args,
            cmd.channel,
            cmd.thread,
        )
        try:
            ticker = args[0].lower().strip()
            quantity = args[1].lower().strip()
        except:
            self.postMessage(
                channel,
                "`crypto sell <ticker> <quantity>` is the format you're looking for.",
                thread,
            )
            return
        try:
            self.trader.sell(user_name, ticker, quantity)
            self.postMessage(
                channel,
                "{u} sold {t} x {q}".format(u=user_name, t=ticker, q=quantity),
                thread,
            )
            self.onLeaderboard(cmd)
        except InsufficientCoinsError:
            self.postMessage(
                channel,
                "{u} does not have {t} x {q} to sell!".format(
                    u=user_name, t=ticker, q=quantity
                ),
                thread,
            )
        except:
            self.postMessage(channel, "Something went wrong.", thread)

    def _onLeaderboard(self, channel: str, thread: Optional[str]):
        png = self.trader.leaderboard()
        try:
            if self.lastLeaderboard:
                self.api_call("files.delete", file=self.lastLeaderboard)
                self.lastLeaderboard = None
            response = self.api_call(
                "files.upload", channels=[channel], filename="leaderboard.png", file=png
            )
            self.lastLeaderboard = response["file"]["id"]
        except:
            self.postMessage(channel, "Something went wrong.", thread)

    def onLeaderboard(self, cmd: Command):
        # crypto leaderboard
        channel, thread = (cmd.channel, cmd.thread)
        self._onLeaderboard(channel, thread)

    def onPrices(self, cmd: Command):
        # example slack command:
        # "crypto price BTC ETH"
        tickers, channel, thread = cmd.args, cmd.channel, cmd.thread
        res = {
            ticker + ": " + str(price)
            for ticker, price in self.trader.api.getPrices().items()
            if ticker.lower() in map(lambda t: t.lower(), tickers)
        }
        self.postMessage(channel, _mono(", ".join(res)), thread)

    def onTopCoins(self, cmd: Command):
        # example slack commands:
        # crypto top
        # crypto top 100
        args, channel, thread = cmd.args, cmd.channel, cmd.thread
        try:
            numCoins = int(args[0]) if args else 10
            numCoins = numCoins if numCoins <= 25 else 25
            png = self.trader.topCoins(numCoins)

            if self.lastTopCoins:
                self.api_call("files.delete", file=self.lastTopCoins)
                self.lastTopCoins = None
            response = self.api_call(
                "files.upload", channels=[channel], filename="top coins.png", file=png
            )
            self.lastTopCoins = response["file"]["id"]
        except:
            self.postMessage
            (channel, "crypto top <numCoins> ... try again", thread)


def _mono(str):
    return "```{str}```".format(str=str)

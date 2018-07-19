from .CryptoTrader import (
    CryptoTrader,
    InsufficientFundsError,
    InsufficientCoinsError
)
from bot.Bot import Bot, Command, SlackBot


class CryptoBot(SlackBot):

    def __init__(
        self,
        token,
        bot: Bot,
        trader: CryptoTrader
    ) -> None:
        super().__init__(token, bot, None)
        self.trader = trader

    def onHelp(self, cmd: Command):
        # crypto help
        channel, thread = cmd.channel, cmd.thread
        msg = "\n".join(
            [
                "crypto help",
                "crypto leaderboard",
                "crypto buy <ticker> <quantity>",
                "crypto sell <ticker> <quantity>",
                "crypto price <ticker>",
                "crypto listings"
            ]
        )
        self.postMessage(
            channel,
            _mono(msg),
            thread
        )

    def onBuy(self, cmd: Command):
        # crypto buy eth 200
        user_name, args, channel, thread = (
            cmd.user_name,
            cmd.args,
            cmd.channel,
            cmd.thread
        )
        ticker = args[0].lower()
        quantity = float(args[1])
        try:
            self.trader.buy(user_name, ticker, quantity)
            self.postMessage(
                channel,
                "{u} bought {t} x {q}"
                .format(u=user_name, t=ticker, q=quantity),
                thread
            )
            self.onLeaderboard(cmd)
        except InsufficientFundsError:
            self.postMessage(
                channel,
                "Insufficient funds. Try selling some coins for $!",
                thread
            )
        except:
            self.postMessage(
                channel,
                "Something went wrong.",
                thread
            )

    def onSell(self, cmd: Command):
        # crypto sell eth 200
        user_name, args, channel, thread = (
            cmd.user_name,
            cmd.args,
            cmd.channel,
            cmd.thread
        )
        ticker = args[0].lower()
        quantity = float(args[1])
        try:
            self.trader.sell(user_name, ticker, quantity)
            self.postMessage(
                channel,
                "{u} sold {t} x {q}"
                .format(u=user_name, t=ticker, q=quantity),
                thread
            )
            self.onLeaderboard(cmd)
        except InsufficientCoinsError:
            self.postMessage(
                channel,
                "{u} does not have {t} x {q} to sell!"
                .format(u=user_name, t=ticker, q=quantity),
                thread
            )
        except:
            self.postMessage(
                channel,
                "Something went wrong.",
                thread
            )

    def onLeaderboard(self, cmd: Command):
        # crypto leaderboard
        channel, thread = (
            cmd.channel,
            cmd.thread
        )
        self.postMessage(
            channel,
            _mono(self.trader.leaderboard()),
            thread
        )

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

    def onListings(self, cmd: Command):
        channel, thread = cmd.channel, cmd.thread
        str = ", ".join(
            list(map(lambda d: d.symbol, self.trader.api.getListings().data)))
        self.postMessage(channel, _mono(str), thread)


def _mono(str):
    return "```{str}```".format(str=str)
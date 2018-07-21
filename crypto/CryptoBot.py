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
                "crypto top",
                "crypto buy <ticker> <quantity>",
                "crypto sell <ticker> <quantity>",
                "crypto price <ticker>"
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
        try:
            ticker = args[0].lower()
            quantity = float(args[1])
        except:
            self.postMessage(
                channel,
                "`crypto buy <ticker> <quantity>` is the format you're looking for.",
                thread
            )
            return
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
        try:
            ticker = args[0].lower()
            quantity = float(args[1])
        except:
            self.postMessage(
                channel,
                "`crypto sell <ticker> <quantity>` is the format you're looking for.",
                thread
            )
            return
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
        channel = (
            cmd.channel
        )
        png = self.trader.leaderboard()
        self.api_call(
            'files.upload',
            channels=[channel],
            filename='leaderboard.png',
            file=png
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

    def onTopCoins(self, cmd: Command):
        # example slack commands:
        # crypto top
        # crypto top 100
        args, channel, thread = cmd.args, cmd.channel, cmd.thread
        try:
            numCoins = int(args[0]) if args else 10
            numCoins = numCoins if numCoins <= 25 else 25
            png = self.trader.topCoins(numCoins)
            self.api_call(
                'files.upload',
                channels=[channel],
                filename='top coins.png',
                file=png
            )
        except:
            self.postMessage
            (
                channel, 'crypto top <numCoins> ... try again', thread
            )


def _mono(str):
    return "```{str}```".format(str=str)

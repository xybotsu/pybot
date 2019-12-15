from .CryptoTrader import (
    CryptoTrader,
    Error,
    InsufficientFundsError,
    InsufficientCoinsError
)
from bot.Bot import Bot, Command, SlackBot
from typing import List, Union
from threading import Timer


class CryptoBot(SlackBot):

    def __init__(
        self,
        token,
        bot: Bot,
        trader: CryptoTrader
    ) -> None:
        super().__init__(token, bot, None)
        self.trader = trader
        self.lastLeaderboard: Union[str, None] = None
        self.lastTopCoins: Union[str, None] = None
        self.runMaintenance(5 * 60)

    def runMaintenance(self, interval: float) -> None:
        self.trader.checkStops()
        Timer(interval, self.runMaintenance, [interval]).start()

    def deleteFileUploads(self, file):
        try:
            result = self.api_call(
                'files.delete',
                file=file
            )
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
                "crypto price <ticker>",
                "crypto play",
                "crypto quit"
            ]
        )
        self.postMessage(
            channel,
            _mono(msg),
            thread
        )

    def onPing(self, cmd: Command):
        channel, thread = cmd.channel, cmd.thread
        self.postMessage(
            channel,
            'pong!',
            thread
        )

    def onNewUser(self, cmd: Command):
        # crypto play
        user_name, args, channel, thread = (
            cmd.user_name,
            cmd.args,
            cmd.channel,
            cmd.thread
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
            cmd.thread
        )
        # delete user here...
        self.trader.delete_user(user_name)
        self.onLeaderboard(cmd)

    def onGetStops(self, cmd: Command):
        user_name, args, channel, thread = (
            cmd.user_name,
            cmd.args,
            cmd.channel,
            cmd.thread
        )
        stops = self.trader.getStops(user_name)
        out: List = ["List of stops for {u}:".format(u=user_name)]
        for stopID, (ticker, qty, stopPrice) in stops.items():
            out.append("{id}:\t{t}\t{q}\t{p}".format(
                id=stopID,
                t=ticker,
                q=qty,
                p=stopPrice
            ))
        self.postMessage(
            channel,
            "\n".join(out),
            thread
        )

    def onSetStop(self, cmd: Command):
        user_name, args, channel, thread = (
            cmd.user_name,
            cmd.args,
            cmd.channel,
            cmd.thread
        )
        try:
            ticker = args[0].lower()
            quantity = float(args[1])
            price = float(args[2])
        except:
            self.postMessage(
                channel,
                "`crypto setstop <ticker> <quantity> <stopPrice>` is the format you're looking for.",
                thread
            )
            return
        res = self.trader.addStop(user_name, (ticker, quantity, price))
        if (isinstance(res, Error)):
            self.postMessage(channel,str(Error),thread)
        else:
            self.onGetStops(cmd)

    def onUpdateStop(self, cmd: Command):
        user_name, args, channel, thread = (
            cmd.user_name,
            cmd.args,
            cmd.channel,
            cmd.thread
        )
        try:
            stopID = int(args[0])
            ticker = args[1].lower()
            quantity = float(args[2])
            price = float(args[3])
        except:
            self.postMessage(
                channel,
                "`crypto updatestop <stopID> <ticker> <quantity> <stopPrice>` is the format you're looking for.",
                thread
            )
            return
        res = self.trader.updateStop(user_name, stopID, (ticker, quantity, price))
        if (isinstance(res, Error)):
            self.postMessage(channel,str(Error),thread)
        else:
            self.onGetStops(cmd)

    def onDeleteStop(self, cmd: Command):
        user_name, args, channel, thread = (
            cmd.user_name,
            cmd.args,
            cmd.channel,
            cmd.thread
        )
        try:
            stopID = int(args[0])
        except:
            self.postMessage(
                channel,
                "`crypto cancelstop <stopID>` is the format you're looking for.",
                thread
            )
            return
        res = self.trader.deleteStop(user_name, stopID)
        if (isinstance(res, Error)):
            self.postMessage(channel,str(Error),thread)
        else:
            self.onGetStops(cmd)

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
        channel, thread = (
            cmd.channel,
            cmd.thread
        )
        png = self.trader.leaderboard()
        try:
            if self.lastLeaderboard:
                self.api_call('files.delete', file=self.lastLeaderboard)
                self.lastLeaderboard = None
            response = self.api_call(
                'files.upload',
                channels=[channel],
                filename='leaderboard.png',
                file=png
            )
            self.lastLeaderboard = response['file']['id']
        except:
            self.postMessage(
                channel,
                "Something went wrong.",
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
                self.api_call('files.delete', file=self.lastTopCoins)
                self.lastTopCoins = None
            response = self.api_call(
                'files.upload',
                channels=[channel],
                filename='top coins.png',
                file=png
            )
            self.lastTopCoins = response['file']['id']
        except:
            self.postMessage
            (
                channel, 'crypto top <numCoins> ... try again', thread
            )


def _mono(str):
    return "```{str}```".format(str=str)

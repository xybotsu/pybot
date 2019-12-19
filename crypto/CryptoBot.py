from .CryptoTrader import (
    CryptoTrader,
    InsufficientFundsError,
    InsufficientCoinsError
)
from bot.Bot import Bot, Command, SlackBot
from typing import List, Union


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
                "crypto if <condition> <action>",
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
            cmd.thread
        )

        print(args)

        # crypto if
        if len(args) == 0:
            # ifs = self.trader.getIfs(user_name)
            self.postMessage(
                channel,
                "displaying ifs for {}".format(
                    user_name
                ),
                thread
            )

        # crypto if delete <id>
        elif args[0] == 'delete':
            try:
                print('delete')
                print(args)
                id = int(args[1])
                # self.trader.deleteIf(user_name, id)
                self.postMessage(
                    channel,
                    "{} wants to delete {}".format(
                        user_name,
                        id
                    ),
                    thread
                )
            except Exception as e:
                print(e)
                self.postMessage(
                    channel,
                    "`crypto delete <id>` is the format you're looking for.",
                    thread
                )

        # crypto if btc > 100 alert
        # crypto if btc > 100 buy btc 100
        else:
            try:
                coin = args[0]
                comparator = args[1]
                amount = float(args[2])
                action = args[3]
                if action == 'alert':
                    print('alert', args)
                    # self.trader.setAlertIf(user_name, coin, comparator, amount)
                    self.postMessage(
                        channel,
                        "{} wants an alert when {} {} {}".format(
                            user_name,
                            coin,
                            comparator,
                            amount
                        ),
                        thread
                    )
                elif action == 'buy':
                    print('buy', args)
                    buyCoin = args[4]
                    buyQty = args[5]
                    # self.trader.setBuyIf(
                    #     user_name, coin, comparator, amount, buyCoin, buyQty)
                    self.postMessage(
                        channel,
                        "{} wants to buy {} {} if {} {} {}".format(
                            user_name,
                            buyQty,
                            buyCoin,
                            coin,
                            comparator,
                            amount
                        ),
                        thread
                    )
                elif action == 'sell':
                    print('sell', args)
                    sellCoin = args[4]
                    sellQty = args[5]
                    # self.trader.setSellIf(
                    #     user_name, coin, comparator, amount, sellCoin, sellQty)
                    self.postMessage(
                        channel,
                        "{} wants sell {} {} if {} {} {}".format(
                            user_name,
                            sellQty,
                            sellCoin,
                            coin,
                            comparator,
                            amount
                        ),
                        thread
                    )
            except Exception as e:
                print(e)
                msg = "\n".join(
                    [
                        "example commands",
                        "crypto if btc > 100 alert",
                        "crypto if btc > 100 sell btc max",
                        "crypto if btc > 100 sell btc 10",
                        "crypto if btc < 50 buy btc max",
                        "crypto if btc < 50 buy btc 10"
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

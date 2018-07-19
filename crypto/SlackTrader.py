from .CryptoTrader import (
    CryptoTrader,
    InsufficientFundsError,
    InsufficientCoinsError
)
from .CoinMarketCap import getListings, getPrices


class SlackTrader(CryptoTrader):

    def onHelp(self, slack, cmd):
        # crypto help
        channel, thread = cmd.channel, cmd.thread
        msg = "\n".join(
            [
                "crypto help",
                "crypto buy <ticker> <quantity>",
                "crypto sell <ticker> <quantity>",
                "crypto price <ticker>",
                "crypto status",
                "crypto listings"
            ]
        )
        slack.rtm_send_message(
            channel,
            _mono(msg),
            thread
        )

    def onBuy(self, slack, cmd):
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
            self.buy(user_name, ticker, quantity)
            slack.rtm_send_message(
                channel,
                "{u} bought {t} x {q}"
                .format(u=user_name, t=ticker, q=quantity),
                thread
            )
            self.onStatus(slack, cmd)
        except InsufficientFundsError:
            slack.rtm_send_message(
                channel,
                "Insufficient funds. Try selling some coins for $!",
                thread
            )
        except:
            slack.rtm_send_message(
                channel,
                "Something went wrong.",
                thread
            )

    def onSell(self, slack, cmd):
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
            self.sell(user_name, ticker, quantity)
            slack.rtm_send_message(
                channel,
                "{u} sold {t} x {q}"
                .format(u=user_name, t=ticker, q=quantity),
                thread
            )
            self.onStatus(slack, cmd)
        except InsufficientCoinsError:
            slack.rtm_send_message(
                channel,
                "{u} does not have {t} x {q} to sell!"
                .format(u=user_name, t=ticker, q=quantity),
                thread
            )
        except:
            slack.rtm_send_message(
                channel,
                "Something went wrong.",
                thread
            )

    def onStatus(self, slack, cmd):
        # crypto status
        user_name, channel, thread = (
            cmd.user_name,
            cmd.channel,
            cmd.thread
        )
        slack.rtm_send_message(
            channel,
            self.status(user_name),
            thread
        )

    def onPrices(self, slack, cmd):
        # example slack command:
        # "crypto price BTC ETH"
        tickers, channel, thread = cmd.args, cmd.channel, cmd.thread
        res = {
            ticker + ": " + str(price)
            for ticker, price in getPrices().items()
            if ticker.lower() in map(lambda t: t.lower(), tickers)
        }
        slack.rtm_send_message(channel, _mono(", ".join(res)), thread)

    def onListings(self, slack, cmd):
        channel, thread = cmd.channel, cmd.thread
        str = ", ".join(list(map(lambda d: d.symbol, getListings().data)))
        slack.rtm_send_message(channel, _mono(str), thread)


def _mono(str):
    return "```{str}```".format(str=str)

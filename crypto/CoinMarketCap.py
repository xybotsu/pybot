from requests import get
from json import loads, JSONDecoder
from .models import Listings, ListingsDecoder, Tickers, TickersDecoder


URL = 'https://api.coinmarketcap.com/v2/{resource}'


def getListings() -> Listings:
    resp = get(URL.format(resource='listings'))
    return loads(resp.text, cls=ListingsDecoder)


def mono(str):
    return "```{str}```".format(str=str)


def onCryptoListings(slack, cmd):
    channel, thread = cmd.channel, cmd.thread
    str = ", ".join(list(map(lambda d: d.symbol, getListings().data)))
    slack.rtm_send_message(channel, mono(str), thread)


def getTickers() -> Tickers:
    resp = get(URL.format(
        resource='ticker/?limit=100&sort=rank&structure=array')
    )
    return loads(resp.text, cls=TickersDecoder)


# example slack command:
# "crypto price BTC ETH"
def onCryptoPrices(slack, cmd):
    tickers, channel, thread = cmd.args, cmd.channel, cmd.thread
    res = [
        ticker.symbol + ': ' + str(ticker.quotes['USD'].price)
        for ticker in getTickers().data
        if ticker.symbol.lower() in map(lambda t: t.lower(), tickers)
    ]
    slack.rtm_send_message(channel, mono(", ".join(res)), thread)

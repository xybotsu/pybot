from bot.Bot import Bot, Command, SlackBot
from redis import StrictRedis
from requests import get
from collections import namedtuple
from datetime import datetime
from pytz import timezone, utc
import time
import re
import os

class ArbitrageBot(SlackBot):
    BOT_REFRESH_TIME = 5 * 60 # CyrptoBot refreshes every 5 min
    HAX_TIME = 0.5 * 60 * 60 # Do hax for 30 min at a time
    HAX_BUFFER = 5 # Do checks 5 sec before CryptoBot refresh
    HAX_CASH = 1e5 # Play with 100k
    BOT_NAME = "cryptobot"
    BOT_CHANNEL = "GBYUB4398" # Channel for arbitragebot to ask cryptobot for latest BTC price

    def __init__(self, token, bot: Bot, db: StrictRedis) -> None:
        super().__init__(token, bot, db)
        self.coinList = list(_pollCmc())

    def onPredict(self, cmd: Command):
        # "crypto hax"
        channel, thread = cmd.channel, cmd.thread
        self.haxUntil = time.time() + ArbitrageBot.HAX_TIME
        print("checking for hax until {}".format(_get_time_str(self.haxUntil)))
        # Poll cryptobot for latest BTC price
        # This should start the cache timer assuming nobody has requested prices in the last 5 min
        self.botPriceHash, self.nextBotUpdateTime = self._pollCryptoBot(channel, thread, self.coinList)
        self._doHax(channel, thread)

    def _doHax(self, channel, thread):
        totalGainz = 0
        opportunities = 0
        while True:
            if time.time() > self.haxUntil:
                self._kaha_msg(channel, thread, "Haxed ${:0.2f} over {} trades.".format(totalGainz, opportunities))
                print("done checking for hax.")
                break

            nextCheck = self.nextBotUpdateTime - ArbitrageBot.HAX_BUFFER
            print("sleep until {}".format(_get_time_str(nextCheck)))
            _sleep_until(nextCheck)
            print("checking for hax...")

            # Get data from CoinMarketCap API
            coinDict = _pollCmc()
            self.coinList = list(coinDict.keys())

            bestGainz = 1
            for coin in self.coinList:
                if not coin in coinDict or not coin in self.botPriceHash:
                    continue
                if coinDict[coin].rank >= 90:
                    continue
                gainz = coinDict[coin].price/self.botPriceHash[coin]
                if gainz > bestGainz:
                    bestGainz = gainz
                    bestCoin = coin

            if bestGainz > 1.01:
                opportunities += 1
                print("best coin {}, up by {:0.2f}%".format(bestCoin, bestGainz-1))
                buyAmt = round(ArbitrageBot.HAX_CASH/self.botPriceHash[coin], 6)
                print("${} worth is {}".format(ArbitrageBot.HAX_CASH, buyAmt))
                self._kaha_msg(channel, thread, "crypto buy {} {}".format(bestCoin, buyAmt))
            else:
                print("no hax this round.")

            # force cache update so we can track price
            _sleep_until(self.nextBotUpdateTime + 1)
            self.botPriceHash, self.nextBotUpdateTime = self._pollCryptoBot(channel, thread, self.coinList)

            if bestGainz > 1.01:
                profit = buyAmt * self.botPriceHash[bestCoin] - ArbitrageBot.HAX_CASH
                totalGainz += profit
                self._kaha_msg(channel, thread, "crypto sell {} {}".format(bestCoin, buyAmt))
                print("Profit of ${:0.2f}".format(profit))

    def _pollCryptoBot(self, errChannel, errThread, coinList):
            # Message cryptobot to get latest coin prices
            self.api_call(
                "chat.postMessage",
                channel=ArbitrageBot.BOT_CHANNEL,
                text="crypto price {}".format(' '.join(coinList)),
                thread_ts=None,
                as_user="true"
            )
            # Wait for cyrptobot reply
            # {'text': '```btc: 8205.06```', 'username': 'cryptobot', 'icons': {'emoji': ':doge:'},
            # 'bot_id': 'BBPBDQN2D', 'type': 'message', 'subtype': 'bot_message', 'team': 'T0339440S',
            # 'channel': 'DBPQ0H3H9', 'event_ts': '1532846653.000009', 'ts': '1532846653.000009'}
            timeout = time.time() + 10
            while True:
                events = list(filter(lambda e:
                    e.get('type') == 'message' and
                    e.get('channel') == ArbitrageBot.BOT_CHANNEL and
                    e.get('username') == ArbitrageBot.BOT_NAME,
                self.rtm_read()))
                if len(events) > 0:
                    botPriceHash = {}
                    prices = events[0].get('text').replace("`","")
                    for coinAndPrice in prices.split(", "):
                        # dash price comes out as a telephone number for some reason, skip it for now
                        # dash: <tel:206.3474357|206.3474357>
                        try:
                            m = re.search('([a-zA-Z0-9]+): ([0-9.]+)', coinAndPrice)
                            coin = m.group(1).lower()
                            price = float(m.group(2))
                            botPriceHash[coin] = price
                        except:
                            print("failed to parse {}".format(coinAndPrice))
                    nextBotUpdateTime = time.time() + ArbitrageBot.BOT_REFRESH_TIME
                    return [botPriceHash, nextBotUpdateTime]
                if time.time() > timeout:
                    print("hax timed out waiting for {} reply!".format(ArbitrageBot.BOT_NAME))
                    self.postMessage(errChannel, "hax timed out waiting for {} reply :sob:".format(
                        ArbitrageBot.BOT_NAME), errThread)
                    return [self.botPriceHash, self.nextBotUpdateTime + ArbitrageBot.BOT_REFRESH_TIME]
                time.sleep(0.1)

    def _kaha_msg(self, channel, thread, msg):
        self.api_call(
            "chat.postMessage",
            token=os.getenv('KAHA_TOKEN'),
            channel=channel,
            text=msg,
            thread_ts=thread,
            as_user="true"
        )

def _mono(str):
    return "```{str}```".format(str=str)

def _get_time_str(call_time):
    return datetime.fromtimestamp(call_time, tz=utc).astimezone(timezone('US/Pacific')).strftime('%I:%M:%S %p')

def _sleep_until(timestamp):
    t = time.time()
    if timestamp > t:
        time.sleep(timestamp - t)

def _pollCmc():
    # use exact same query as cryptobot otherwise prices may be different
    resp = get('https://api.coinmarketcap.com/v2/ticker/?limit=100&sort=rank&structure=array').json()
    coinDict = {}
    coinInfo = namedtuple('coinInfo', 'price updateTime rank')
    for coin in resp['data']:
        try:
            name = coin['symbol'].lower()
            price = coin['quotes']['USD']['price']
            rank = coin['rank']
            updateTime = coin['last_updated']
            coinDict[name] = coinInfo(price, updateTime, rank)
        except:
            print("failed to parse {}".format(str(coin)))
    return coinDict

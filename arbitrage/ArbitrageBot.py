from bot.Bot import Bot, Command, SlackBot
from redis import StrictRedis
from requests import get
from datetime import datetime
from pytz import timezone, utc
import time
import re
import os

class ArbitrageBot(SlackBot):
    BOT_REFRESH_TIME = 5 * 60 # CyrptoBot refreshes every 5 min
    CMC_REFRESH_TIME = 1.75 * 60 # CoinMarketCap refreshes every 2-5 min, best to be conservative
    HAX_THRESHOLD = 3 # Only post when profit is more than $3 per btc
    HAX_TIME = 6 * 60 * 60 # Do hax for 6 hours at a time
    HAX_BUFFER = 30 # Do checks 30 sec before CryptoBot refresh
    BOT_NAME = "cryptobot"
    BOT_CHANNEL = "GBYUB4398" # Channel for arbitragebot to ask cryptobot for latest BTC price

    def __init__(self, token, bot: Bot, db: StrictRedis) -> None:
        super().__init__(token, bot, db)

    def onPredict(self, cmd: Command):
        # "crypto hax"
        channel, thread = cmd.channel, cmd.thread
        self.haxUntil = time.time() + ArbitrageBot.HAX_TIME
        print("checking for hax until {}".format(_get_time_str(self.haxUntil)))
        #self.postMessage(channel, "Cryptodamus will check for arbitrage opportunities `{} sec`"
        #                          " before each {} update until `{}`".format(
        #                              ArbitrageBot.HAX_BUFFER,
        #                              ArbitrageBot.BOT_NAME,
        #                              _get_time_str(self.haxUntil)), thread)
        # Poll cryptobot for latest BTC price
        # This should start the cache timer assuming nobody has requested prices in the last 5 min
        self.botPrice, self.nextBotUpdateTime = self._pollCryptoBot(channel, thread)
        self._doHax(channel, thread)

    def _doHax(self, channel, thread):
        gainz = 0
        opportunities = 0
        while True:
            if time.time() > self.haxUntil:
                #self.postMessage(channel, "Done checking for hax.\n"
                #                          "Hax potential was `${:0.2f}` per BTC over `{}` opportunities.".format(
                #                              gainz, opportunities), thread)
                self._kaha_msg(channel, thread, "Haxed ${:0.2f} over {} trades.".format(gainz, opportunities))
                print("done checking for hax.")
                break

            nextCheck = self.nextBotUpdateTime - ArbitrageBot.HAX_BUFFER
            print("sleep until {}".format(_get_time_str(nextCheck)))
            _sleep_until(nextCheck)
            print("checking for hax...")

            # Get data from CoinMarketCap API
            cmcPrice, cmcUpdateTime = _pollCmc()
            cmcPriceVolatile = self.nextBotUpdateTime - cmcUpdateTime > ArbitrageBot.CMC_REFRESH_TIME
            cmcAdvice = " (use caution)" if cmcPriceVolatile else ""
            cmcUpdateAge = time.time() - cmcUpdateTime

            prediction = None
            if self.botPrice < cmcPrice:
                prediction = "go up"
            elif self.botPrice > cmcPrice:
                prediction = "drop"

            priceDiff = abs(cmcPrice-self.botPrice)
            winning = prediction is not None and priceDiff >= ArbitrageBot.HAX_THRESHOLD
            buyThenSell = winning and not cmcPriceVolatile and self.botPrice < cmcPrice
            sellThenBuy = winning and not cmcPriceVolatile and self.botPrice > cmcPrice

            # Should be ~= ArbitrageBot.HAX_BUFFER
            nextBotUpdateSec = self.nextBotUpdateTime - time.time()

            if winning:
                gainz += priceDiff
                opportunities += 1
                print("Price should {} by {:0.2f}...".format(prediction, priceDiff))
                #self.postMessage(channel, "Cryptodamus predicts\n"
                #                            "```BTC price will {} by ${:0.2f} ({:0.2f} -> {:0.2f}) in {:.0f} seconds."
                #                            " CMC price is {:.0f} seconds old{}.```".format(
                #                                prediction, priceDiff, self.botPrice, cmcPrice,
                #                                nextBotUpdateSec, cmcUpdateAge, cmcAdvice), thread)

            # make gainz
            if buyThenSell:
                self._kaha_msg(channel, thread, "crypto buy btc 6")
            elif sellThenBuy:
                self._kaha_msg(channel, thread, "crypto sell btc 6")

            # debug info
            cmcUpdateAge = time.time() - cmcUpdateTime
            print("BOT = {}, CMC = {}, Next bot update in {:.0f}, last CMC update {:.0f} sec ago".format(
                self.botPrice, cmcPrice, nextBotUpdateSec, cmcUpdateAge))

            # force cache update so we can track price
            _sleep_until(self.nextBotUpdateTime + 1)
            self.botPrice, self.nextBotUpdateTime = self._pollCryptoBot(channel, thread)

            # debug info
            cmcPrice, cmcUpdateTime = _pollCmc()
            cmcUpdateAge = time.time() - cmcUpdateTime
            nextBotUpdateSec = round(self.nextBotUpdateTime - time.time())
            print("BOT = {}, CMC = {}, Next bot update in {}, last CMC update {:0.2f} sec ago".format(
                self.botPrice, cmcPrice, nextBotUpdateSec, cmcUpdateAge))
            print("Gainz = {:0.2f}, Opps = {}".format(gainz, opportunities))

            #if winning:
            #    self.postMessage(channel, "{} price is now `${:0.2f}`".format(ArbitrageBot.BOT_NAME, self.botPrice), thread)

            # make gainz
            if buyThenSell:
                self._kaha_msg(channel, thread, "crypto sell btc 6")
            elif sellThenBuy:
                self._kaha_msg(channel, thread, "crypto buy btc 6")

    def _pollCryptoBot(self, errChannel, errThread):
            # Message cryptobot to get latest BTC price
            self.api_call(
                "chat.postMessage",
                channel=ArbitrageBot.BOT_CHANNEL,
                text="crypto price btc",
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
                    m = re.search('[0-9.]+', events[0].get('text'))
                    botPrice = float(m.group(0))
                    nextBotUpdateTime = time.time() + ArbitrageBot.BOT_REFRESH_TIME
                    return [botPrice, nextBotUpdateTime]
                if time.time() > timeout:
                    print("hax timed out waiting for {} reply!".format(ArbitrageBot.BOT_NAME))
                    self.postMessage(errChannel, "hax timed out waiting for {} reply :sob:".format(
                        ArbitrageBot.BOT_NAME), errThread)
                    return [self.botPrice, self.nextBotUpdateTime + ArbitrageBot.BOT_REFRESH_TIME]
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
    cmcPrice = resp['data'][0]['quotes']['USD']['price']
    cmcUpdateTime = resp['data'][0]['last_updated']
    return [cmcPrice, cmcUpdateTime]
    

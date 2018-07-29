from bot.Bot import Bot, Command, SlackBot
from redis import StrictRedis
from requests import get
from datetime import datetime
from pytz import timezone, utc
import time
import re

class ArbitrageBot(SlackBot):
    BOT_REFRESH_TIME = 5 * 60 # CyrptoBot refreshes every 5 min
    CMC_REFRESH_TIME = 1.75 * 60 # CoinMarketCap refreshes every 2-5 min, best to be conservative
    HAX_TIME = 30 * 60 # Do hax for 30 min at a time
    HAX_BUFFER = 30 # Do checks 30 sec before CryptoBot refresh
    BOT_NAME = "cryptobot"
    BOT_CHANNEL = "GBYUB4398" # Channel for arbitragebot to ask cryptobot for latest BTC price

    def __init__(self, token, bot: Bot, db: StrictRedis) -> None:
        super().__init__(token, bot, db)
        self.startTime = time.time()
        self.haxUntil = 0

    def onPredict(self, cmd: Command):
        # "crypto hax"
        channel, thread = cmd.channel, cmd.thread
        call_time = time.time()
        alreadyHaxing = call_time < self.haxUntil
        self.haxUntil = call_time + ArbitrageBot.HAX_TIME
        print("checking for hax until {}".format(_get_time_str(self.haxUntil)))
        self.postMessage(channel, "Cryptodamus will check for arbitrage opportunities `{} sec`"
                                  " before each {} update until `{}`".format(
                                      ArbitrageBot.HAX_BUFFER,
                                      ArbitrageBot.BOT_NAME,
                                      _get_time_str(self.haxUntil)), thread)
        if not alreadyHaxing:
            # TODO run loop in background so we can update hax time mid-loop
            # TODO allow running multiple loops for different channels/threads
            self._doHax(channel, thread)

    def _doHax(self, channel, thread):
        while True:
            if time.time() > self.haxUntil:
                print("done checking for hax.")
                break

            nextBotUpdateTime = _get_next_bot_update_time(self.startTime, time.time() + ArbitrageBot.HAX_BUFFER)
            nextHax = nextBotUpdateTime - ArbitrageBot.HAX_BUFFER
            print("next hax check at {}".format(_get_time_str(nextHax)))
            _sleep_until(nextHax)
            print("checking for hax...")

            # Get data from CoinMarketCap API
            resp = get('https://api.coinmarketcap.com/v2/ticker/?limit=1').json()
            cmcPrice = resp['data']['1']['quotes']['USD']['price']
            cmcUpdateTime = resp['data']['1']['last_updated']

            botPrice = self._pollCryptoBot(channel, thread)

            if nextBotUpdateTime - cmcUpdateTime > ArbitrageBot.CMC_REFRESH_TIME:
                # hax too risky, cmc may update at any moment
                continue

            nextBotUpdateSec = round(nextBotUpdateTime - time.time()) # Should be ~= ArbitrageBot.HAX_BUFFER
            if botPrice < cmcPrice:
                self.postMessage(channel, "Cryptodamus predicts\n"
                                          "```BTC price will go up by ${:0.2f} ({:0.2f} -> {:0.2f}) in {} seconds.```".format(
                                              cmcPrice-botPrice, botPrice, cmcPrice, nextBotUpdateSec), thread)
                # Force cache update
                _sleep_until(nextBotUpdateTime)
                newPrice = self._pollCryptoBot(channel, thread)
                self.postMessage(channel, "{} price is now `${:0.2f}`. Make your gainz!".format(ArbitrageBot.BOT_NAME, newPrice), thread)
            elif botPrice > cmcPrice:
                self.postMessage(channel, "Cryptodamus predicts\n"
                                          "```BTC price will drop by ${:0.2f} ({:0.2f} -> {:0.2f}) in {} seconds.```".format(
                                              botPrice-cmcPrice, botPrice, cmcPrice, nextBotUpdateSec), thread)
                # Force cache update
                _sleep_until(nextBotUpdateTime)
                newPrice = self._pollCryptoBot(channel, thread)
                self.postMessage(channel, "{} price is now `${:0.2f}`. Make your gainz!".format(ArbitrageBot.BOT_NAME, newPrice), thread)
            #else prices are equal, wait for next bot update

            print("BOT = {}, CMC = {}, Next bot update in {}".format(botPrice, cmcPrice, nextBotUpdateSec))

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
            timeout = time.time() + 5
            while True:
                events = list(filter(lambda e:
                    e.get('type') == 'message' and
                    e.get('channel') == ArbitrageBot.BOT_CHANNEL and
                    e.get('username') == ArbitrageBot.BOT_NAME,
                self.rtm_read()))
                if len(events) > 0:
                    m = re.search('[0-9.]+', events[0].get('text'))
                    botPrice = float(m.group(0))
                    return botPrice
                if time.time() > timeout:
                    print("hax timed out waiting for {} reply!".format(ArbitrageBot.BOT_NAME))
                    self.postMessage(errChannel, "hax timed out waiting for {} reply :sob:".format(
                        ArbitrageBot.BOT_NAME), errThread)
                    return 0
                time.sleep(0.1)

def _mono(str):
    return "```{str}```".format(str=str)

def _get_time_str(call_time):
    return datetime.fromtimestamp(call_time, tz=utc).astimezone(timezone('US/Pacific')).strftime('%I:%M:%S %p')

def _get_next_bot_update_time(startTime, call_time):
    upTime = call_time - startTime
    return call_time - (upTime % ArbitrageBot.BOT_REFRESH_TIME) + ArbitrageBot.BOT_REFRESH_TIME

def _sleep_until(timestamp):
    t = time.time()
    if timestamp > t:
        time.sleep(timestamp - t)

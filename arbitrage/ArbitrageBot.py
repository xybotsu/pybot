from bot.Bot import Bot, Command, SlackBot
from requests import get
from datetime import datetime
from pytz import timezone, utc
import time
import re

class ArbitrageBot(SlackBot):
    BOT_REFRESH_TIME = 5 * 60 # CyrptoBot refreshes every 5 min
    CMC_REFRESH_TIME = 2 * 60 # CoinMarketCap refreshes every 2-5 min, best to be conservative

    def __init__(self, token, bot: Bot, ) -> None:
        super().__init__(token, bot, None)
        self.startTime = time.time()
        '''
        self.lastBotPrice = None
        self.lastCall = None
        self.next_time1 = None
        self.next_time2 = None
        '''

    def onPredict(self, cmd: Command):
        # "crypto hax"
        args, channel, thread, ts = cmd.args, cmd.channel, cmd.thread, cmd.event.ts
        call_time = time.time()

        # Get data from CoinMarketCap API
        resp = get('https://api.coinmarketcap.com/v2/ticker/?limit=1').json()
        cmcPrice = resp['data']['1']['quotes']['USD']['price']
        cmcUpdateTime = resp['data']['1']['last_updated']

        botPrice = 0
        upTime = call_time - self.startTime
        botUpdateTime = call_time - (upTime % ArbitrageBot.BOT_REFRESH_TIME)
        # Message cryptobot to get latest BTC price
        self.api_call(
            "chat.postMessage",
            channel=channel,
            text="crypto price btc",
            thread_ts=thread,
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
                e.get('channel') == channel and
                e.get('thread_ts') == thread and
                e.get('username') == 'cryptobot',
            self.rtm_read()))
            if len(events) > 0:
                m = re.search('[0-9.]+', events[0].get('text'))
                botPrice = float(m.group(0))
                break
            if time.time() > timeout:
                print("hax timed out waiting for cryptobot reply!")
                self.postMessage(channel, "hax timed out waiting for cryptobot reply :sob:", thread)
                return
            time.sleep(0.1)

        advice = ''
        timeDiff = ArbitrageBot.BOT_REFRESH_TIME - ArbitrageBot.CMC_REFRESH_TIME
        nextBotUpdateTime = botUpdateTime + ArbitrageBot.BOT_REFRESH_TIME

        nextCmcUpdateTime = ''
        if call_time - cmcUpdateTime > ArbitrageBot.CMC_REFRESH_TIME:
            nextCmcUpdateTime = _get_time_str(call_time+30)
        else:
            nextCmcUpdateTime = _get_time_str(cmcUpdateTime+ArbitrageBot.CMC_REFRESH_TIME)
    
        if nextBotUpdateTime - cmcUpdateTime > ArbitrageBot.CMC_REFRESH_TIME:
            advice = "wait for next CoinMarketCap update."
        elif call_time - botUpdateTime < timeDiff:
            advice = "cryptobot data too fresh, ask again at {}.".format(_get_time_str(botUpdateTime+timeDiff))
        elif botPrice < cmcPrice:
            advice = "401k -> BTC"
        else:
            advice = "lock in those gainz!"

        self.postMessage(channel, _mono('MarketCap BTC Price: ${:.2f} as of {}\n'
                                        'cryptobot BTC Price: ${:.2f} as of {}\n'
                                        'Current time is          {}\n'
                                        'Next MarketCap update is {}-ish\n'
                                        'Next cryptobot update is {}\n'
                                        'Advice... {}'.format(
            cmcPrice, _get_time_str(cmcUpdateTime), botPrice, _get_time_str(botUpdateTime),
            _get_time_str(call_time), nextCmcUpdateTime, _get_time_str(nextBotUpdateTime), advice)), thread)

# We have logic to hone in on the next update time with enough calls to hax
# but we can also cheat since we use the same clock and save people the spam
'''
        update_time = resp['data']['1']['last_updated']
        call_time = time.time()
        if self.lastBotPrice is None:
            self.lastBotPrice = botPrice
            self.lastCall = call_time
            self.next_time1 = call_time
            self.next_time2 = call_time + ArbitrageBot.BOT_REFRESH_TIME
        else:
            if call_time >= self.next_time1 and call_time <= self.next_time2:
                if botPrice == self.lastBotPrice:
                    self.next_time1 = call_time
                else:
                    self.uncertainty = call_time - self.lastCall
                    self.next_time1 = self.lastCall + ArbitrageBot.BOT_REFRESH_TIME
                    self.next_time2 = call_time + ArbitrageBot.BOT_REFRESH_TIME
            else:
                spread = self.next_time2 - self.next_time1
                self.next_time1 = call_time - (call_time % ArbitrageBot.BOT_REFRESH_TIME) + (self.next_time1 % ArbitrageBot.BOT_REFRESH_TIME)
                # TODO cannot update from within a window because price will always
                # be different and we use price difference to set the window...
                # not a big deal since window will likely be small most of the time
                if self.next_time1 < call_time:
                    self.next_time1 += ArbitrageBot.BOT_REFRESH_TIME
                self.next_time2 = self.next_time1 + spread
            self.lastCall = call_time
            self.lastBotPrice = botPrice
        self.postMessage(channel, _mono('CoinMarketCap BTC Price: {} as of {}\n'
                                        'cryptobot BTC Price: {}\n'
                                        'cryptobot update window {} - {}'.format(
            cmcPrice, _get_time_str(update_time), botPrice, _get_time_str(self.next_time1), _get_time_str(self.next_time2))), thread)
'''
def _mono(str):
    return "```{str}```".format(str=str)

def _get_time_str(call_time):
    return datetime.fromtimestamp(call_time, tz=utc).astimezone(timezone('US/Pacific')).strftime('%I:%M:%S %p')
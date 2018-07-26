from bot.Bot import Bot, Command, SlackBot
from requests import get
from datetime import datetime

class ArbitrageBot(SlackBot):

    def __init__(
        self,
        token,
        bot: Bot
    ) -> None:
        super().__init__(token, bot, None)

    def onPredict(self, cmd: Command):
        # "crypto hax"
        args, channel, thread = cmd.args, cmd.channel, cmd.thread
        resp = get('https://api.coinmarketcap.com/v2/ticker/?limit=1').json()
        price = resp['data']['1']['quotes']['USD']['price']
        update_time = resp['data']['1']['last_updated']
        time_str = datetime.fromtimestamp(update_time).strftime('%I:%M:%S %p')
        self.api_call(
            "chat.postMessage",
            channel=channel,
            text="crypto price btc",
            thread_ts=thread,
            as_user="true"
        )
        self.postMessage(channel, _mono('btc: {} as of {}'.format(price, time_str)), thread)

def _mono(str):
    return "```{str}```".format(str=str)

import logging

from .chessmanager import ChessManager
from bot.Bot import Bot, threadedMessageEvents, allMessageEvents
from bot.config import SLACK_TOKEN
from bot.redis import redis
from slackclient import SlackClient
from crypto.CryptoTrader import CryptoTrader
from crypto.SlackTrader import SlackTrader

if __name__ == '__main__':
    try:
        chess = ChessManager(redis)
        bot = Bot(SlackClient(SLACK_TOKEN))

        # chess routes
        bot.register('chess ai', chess.onAi, threadedMessageEvents)
        bot.register('chess start', chess.onStart, threadedMessageEvents)
        bot.register('chess claim', chess.onClaim, threadedMessageEvents)
        bot.register('chess board', chess.onBoard, threadedMessageEvents)
        bot.register('chess move', chess.onMove, threadedMessageEvents)
        bot.register('chess takeback', chess.onTakeback, threadedMessageEvents)
        bot.register('chess forfeit', chess.onForfeit, threadedMessageEvents)
        bot.register('chess record', chess.onRecord, threadedMessageEvents)
        bot.register('chess leaderboard', chess.onLeaderboard,
                     threadedMessageEvents)
        bot.register('chess help', chess.onHelp, threadedMessageEvents)

        # trading routes
        trader = SlackTrader(
            redis,
            'test',
            'Crypto Bot',
            'https://www.dogecoingold.com/wp-content/uploads/2017/11/new-logo-1.png'
        )
        bot.register('crypto list', trader.onListings, allMessageEvents)
        bot.register('crypto prices', trader.onPrices, allMessageEvents)
        bot.register('crypto price', trader.onPrices, allMessageEvents)
        bot.register('crypto buy', trader.onBuy, allMessageEvents)
        bot.register('crypto sell', trader.onSell, allMessageEvents)
        bot.register('crypto status', trader.onStatus, allMessageEvents)
        bot.register('crypto help', trader.onHelp, allMessageEvents)

        # start listening
        bot.listen()

    except Exception as e:  # die on any other error
        logging.exception('Error bubbled up to main loop')

import logging

from .chessmanager import ChessManager
from bot.Bot import Bot, threadedMessageEvents, messageEvents
from bot.config import SLACK_TOKEN
from bot.redis import redis
from crypto.CoinMarketCap import getListings, onCryptoListings, onCryptoPrices
from slackclient import SlackClient


if __name__ == '__main__':
    try:
        chess = ChessManager(redis)
        bot = Bot(SlackClient(SLACK_TOKEN))

        # routes
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

        bot.register('crypto list', onCryptoListings, messageEvents)
        bot.register('crypto prices', onCryptoPrices, messageEvents)

        # start listening
        bot.listen()
    except Exception as e:  # die on any other error
        logging.exception('Error bubbled up to main loop')

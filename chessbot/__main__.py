import logging

from .ChessBot import ChessBot
from bot.Bot import SlackBot, Bot, threaded, allMessageEvents
from bot.config import SLACK_TOKEN
from bot.redis import redis
from slackclient import SlackClient
from crypto.CryptoTrader import CryptoTrader
from crypto.SlackTrader import CryptoBot
from multiprocessing import Process


if __name__ == '__main__':
    try:
        chess = ChessBot(
            SLACK_TOKEN,
            Bot(
                'chessbot',
                'https://avatars.slack-edge.com/2018-07-12/397402417555_1930b48e0e8bc72941aa_48.png'
            ),
            redis
        )

        # chess routes
        chess.register('chess start', chess.onStart, threaded)
        chess.register('chess claim', chess.onClaim, threaded)
        chess.register('chess board', chess.onBoard, threaded)
        chess.register('chess move', chess.onMove, threaded)
        chess.register('chess takeback', chess.onTakeback, threaded)
        chess.register('chess forfeit', chess.onForfeit, threaded)
        chess.register('chess record', chess.onRecord, threaded)
        chess.register('chess leaderboard', chess.onLeaderboard, threaded)
        chess.register('chess help', chess.onHelp, allMessageEvents)

        # trading routes
        crypto = CryptoBot(
            SLACK_TOKEN,
            Bot(
                'cryptobot',
                'https://www.dogecoingold.com/wp-content/uploads/2017/11/new-logo-1.png'
            ),
            CryptoTrader(redis, 'test')
        )
        crypto.register('crypto list', crypto.onListings, allMessageEvents)
        crypto.register('crypto prices', crypto.onPrices, allMessageEvents)
        crypto.register('crypto price', crypto.onPrices, allMessageEvents)
        crypto.register('crypto buy', crypto.onBuy, allMessageEvents)
        crypto.register('crypto sell', crypto.onSell, allMessageEvents)
        crypto.register('crypto status', crypto.onStatus, allMessageEvents)
        crypto.register('crypto help', crypto.onHelp, allMessageEvents)

        # start listening in parallel
        Process(target=chess.listen).start()
        Process(target=crypto.listen).start()

    except Exception as e:  # die on any other error
        logging.exception('Error bubbled up to main loop')

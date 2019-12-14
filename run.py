import logging

from chessbot.ChessBot import ChessBot
from bot.Bot import SlackBot, Bot, threaded, allMessageEvents
from bot.config import SLACK_TOKEN
from bot.redis import redis
from slackclient import SlackClient
from crypto.CryptoTrader import CryptoTrader
from crypto.CryptoBot import CryptoBot
from arbitrage.ArbitrageBot import ArbitrageBot
from multiprocessing import Process
import http.server
import socketserver
import os


class MyServer(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-type', 'text/html')
        self.end_headers()
        return


if __name__ == '__main__':
    try:
        chess = ChessBot(
            SLACK_TOKEN,
            Bot(
                'chessbot',
                ':chess:'
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
                ':doge:'
            ),
            CryptoTrader(redis, 'test')
        )
        crypto.register('crypto prices', crypto.onPrices, allMessageEvents)
        crypto.register('crypto price', crypto.onPrices, allMessageEvents)
        crypto.register('crypto buy', crypto.onBuy, allMessageEvents)
        crypto.register('crypto sell', crypto.onSell, allMessageEvents)
        crypto.register('crypto leaderboard',
                        crypto.onLeaderboard, allMessageEvents)
        crypto.register('crypto top', crypto.onTopCoins, allMessageEvents)
        crypto.register('crypto help', crypto.onHelp, allMessageEvents)
        crypto.register('crypto play', crypto.onNewUser, allMessageEvents)
        crypto.register('crypto quit', crypto.onUserQuit, allMessageEvents)
        crypto.register('crypto ping', crypto.onPing, allMessageEvents)
        crypto.register('Reminder: crypto ping',
                        crypto.onPing, allMessageEvents)

        # arbitrage bot
        # arbitrage = ArbitrageBot(
        #     SLACK_TOKEN,
        #     Bot(
        #         'cryptodamus',
        #         ':crystal_ball:'
        #     ),
        #     redis
        # )
        # arbitrage.register('crypto hax', arbitrage.onPredict, allMessageEvents)

        # serve images out of img dir
        os.chdir('img')
        Handler = http.server.SimpleHTTPRequestHandler
        httpd = socketserver.TCPServer(("", 8000), Handler)

        server = http.server.HTTPServer(
            ('', int(os.environ['PORT'])), MyServer)

        # start listening in parallel
        Process(target=chess.listen).start()
        Process(target=crypto.listen).start()
        # Process(target=arbitrage.listen).start()
        Process(target=httpd.serve_forever).start()
        Process(target=server.serve_forever).start()

    except Exception as e:  # die on any other error
        logging.exception('Error bubbled up to main loop')

import logging

from .chessmanager import ChessManager
from .Xybotsu import Xybotsu, threadedMessageEvents, slack

if __name__ == '__main__':
  try:
    chess = ChessManager()
    x = Xybotsu(slack)

    # routes
    x.register('chess ai', chess.onAi, threadedMessageEvents)
    x.register('chess start', chess.onStart, threadedMessageEvents)
    x.register('chess claim', chess.onClaim, threadedMessageEvents)
    x.register('chess board', chess.onBoard, threadedMessageEvents)
    x.register('chess move', chess.onMove, threadedMessageEvents)
    x.register('chess takeback', chess.onTakeback, threadedMessageEvents)
    x.register('chess forfeit', chess.onForfeit, threadedMessageEvents)
    x.register('chess record', chess.onRecord, threadedMessageEvents)
    x.register('chess leaderboard', chess.onLeaderboard, threadedMessageEvents)
    x.register('chess help', chess.onHelp, threadedMessageEvents)

    # start listening
    x.listen()
  except Exception as e: # die on any other error
    logging.exception('Error bubbled up to main loop')

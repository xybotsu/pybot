import logging

from .chessmanager import ChessManager
from .Xybotsu import Xybotsu, threadedMessageEvents, slack

if __name__ == '__main__':
  try:
    manager = ChessManager()
    x = Xybotsu(slack)

    # routes
    x.register('chess ai', manager.onAi, threadedMessageEvents)
    x.register('chess start', manager.onStart, threadedMessageEvents)
    x.register('chess claim', manager.onClaim, threadedMessageEvents)
    x.register('chess board', manager.onBoard, threadedMessageEvents)
    x.register('chess move', manager.onMove, threadedMessageEvents)
    x.register('chess takeback', manager.onTakeback, threadedMessageEvents)
    x.register('chess forfeit', manager.onForfeit, threadedMessageEvents)
    x.register('chess record', manager.onRecord, threadedMessageEvents)
    x.register('chess leaderboard', manager.onLeaderboard, threadedMessageEvents)
    x.register('chess help', manager.onHelp, threadedMessageEvents)

    # start listening
    x.listen()
  except Exception as e: # die on any other error
    logging.exception('Error bubbled up to main loop')

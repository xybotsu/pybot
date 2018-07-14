from .board import TarraschBoard, TarraschNoBoardException
from pprint import pprint

class ChessManager:
  def __init__(self):
    self.board = None

  # triggered by 'chess ai'
  def onAi(self, slack, args, event):
    pprint(vars(event))

  # triggered by 'chess start'
  def onStart(self, slack, args, event):
    pprint(vars(event))
    """Start a new game."""
    # try:
    #     self.board = TarraschBoard.from_backend(channel, thread)
    # except TarraschNoBoardException:
    #     self.board = None

    # if board:
    #     return client.rtm_send_message(channel, 'A game is already going on in this channel between {} and {}'.format(board.white_user, board.black_user), thread)
    # STARTUP_STATE[TarraschBoard.getDbKey(channel, thread)] = {}
    # client.rtm_send_message(channel, "Let's play chess! I need two players to say `{0} claim white` or `{0} claim black`.".format(MP), thread)

  # triggered by 'chess claim'
  def onClaim(self, slack, args, event):
    pprint(vars(event))

  # triggered by 'chess board'
  def onBoard(self, slack, args, event):
    pprint(vars(event))

  # triggered by 'chess move'
  def onMove(self, slack, args, event):
    pprint(vars(event))

  # triggered by 'chess takeback'
  def onTakeback(self, slack, args, event):
    pprint(vars(event))

  # triggered by 'chess forfeit'
  def onForfeit(self, slack, args, event):
    pprint(vars(event))

    # triggered by 'chess record'
  def onRecord(self, slack, args, event):
    pprint(vars(event))

    # triggered by 'chess leaderboard'
  def onLeaderboard(self, slack, args, event):
    pprint(vars(event))

    # triggered by 'chess help'
  def onHelp(self, slack, args, event):
    pprint(vars(event))

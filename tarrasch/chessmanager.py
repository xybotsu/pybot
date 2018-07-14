import json
import time

from .analysis import upload_analysis
from .board import TarraschBoard, TarraschNoBoardException
from chess import SQUARE_NAMES
from .config import MESSAGE_PREFIX as MP, COOLDOWN_SECONDS
from .database import singleton as db
from pprint import pprint
from prettytable import PrettyTable

class ChessManager:
  def __init__(self):
    self.STARTUP_STATE = {}

  # triggered by 'chess ai'
  def onAi(self, slack, args, event):
    """Battle an AI."""
    response = "So I hear " + event.user_name + " wants to fight some AI... we're working on it!"
    slack.rtm_send_message(event.channel, response, event.thread)

  # triggered by 'chess start'
  def onStart(self, slack, args, event):
    """Start a new game."""
    channel, thread = event.channel, event.thread
    try:
      board = TarraschBoard.from_backend(channel, thread)
    except TarraschNoBoardException:
      board = None

    if board:
      return slack.rtm_send_message(channel, 'A game is already going on in this channel between {} and {}'.format(board.white_user, board.black_user), thread)
    self.STARTUP_STATE[TarraschBoard.getDbKey(channel, thread)] = {}
    slack.rtm_send_message(channel, "Let's play chess! I need two players to say `{0} claim white` or `{0} claim black`.".format(MP), thread)

  # triggered by 'chess claim'
  def onClaim(self, slack, args, event):
    """Claim a side in the next game. Used after a start command."""
    channel, thread, user_name = event.channel, event.thread, event.user_name
    if TarraschBoard.getDbKey(channel, thread) not in self.STARTUP_STATE:
      return slack.rtm_send_message(channel, 'Say `{} start` to start a new game.'.format(MP), thread)
    
    color = args[0].lower()
    if color not in ['white', 'black']:
      return slack.rtm_send_message(channel, 'Say `{} claim white` or `{} claim black` to pick your side.'.format(MP, MP), thread)

    self.STARTUP_STATE[TarraschBoard.getDbKey(channel, thread)][color] = user_name
    slack.rtm_send_message(channel, '*{}* will play as {}.'.format(user_name, color), thread)

    if 'white' in self.STARTUP_STATE[TarraschBoard.getDbKey(channel, thread)] and 'black' in self.STARTUP_STATE[TarraschBoard.getDbKey(channel, thread)]:
      self._start_game(slack, event, self.STARTUP_STATE[TarraschBoard.getDbKey(channel, thread)]['white'], self.STARTUP_STATE[TarraschBoard.getDbKey(channel, thread)]['black'])
      del self.STARTUP_STATE[TarraschBoard.getDbKey(channel, thread)]

  def _start_game(self, slack, event, white_user, black_user):
    channel, thread = event.channel, event.thread
    board = TarraschBoard(channel, thread, white_user, black_user)
    board.save()
    self._render(slack, event, board)

  def _render(self, slack, event, board=None):
    channel, thread = event.channel, event.thread
    if not board:
      board = TarraschBoard.from_backend(channel, thread)
    slack.rtm_send_message(channel, board.get_url(shorten=True), thread)
    color = 'white' if board.turn else 'black'
    user = board.white_user if color == 'white' else board.black_user
    if not board.is_game_over():
      message = ''
      if board.move_stack:
        last_move = board.move_stack[-1]
        from_square, to_square = SQUARE_NAMES[last_move.from_square], SQUARE_NAMES[last_move.to_square]
        message += 'Last move: {} → {}. '.format(from_square, to_square)
      message += '*{}* ({}) to play.'.format(user, color)
      if board.is_check():
        message += ' Check.'
      slack.rtm_send_message(channel, message, thread)

  # triggered by 'chess board'
  def onBoard(self, slack, args, event):
    """Show the current board state for the game in this channel."""
    self._render(slack, event)

  # triggered by 'chess move'
  def onMove(self, slack, args, event):
    """Make a new move. Use algebraic notation, e.g. `move Nc3`"""
    channel, thread, user_name = event.channel, event.thread, event.user_name
    board = TarraschBoard.from_backend(channel, thread)
    if user_name != board.current_turn_username: # not this person's turn
      return
    if len(args) == 0:
      return
    time_until_can_move = COOLDOWN_SECONDS - (time.time() - board.last_move_time)
    if time_until_can_move > 1:
      return slack.rtm_send_message(channel, 'You must wait {} to make a move.'.format(_humanize(time_until_can_move)), thread)

    move = args[0]
    try:
      board.push_san(move)
    except ValueError:
      return slack.rtm_send_message(channel, 'This move is illegal.', thread)
    board.save(last_move_time=time.time())
    self._render(slack, event, board=board)
    if board.is_game_over():
      self._handle_game_over(slack, event, board)

  # triggered by 'chess takeback'
  def onTakeback(self, slack, args, event):
    """Take back the last move. Can only be done by the current player."""
    channel, thread, user_name = event.channel, event.thread, event.user_name
    board = TarraschBoard.from_backend(channel, thread)
    if user_name != board.current_turn_username:
      return slack.rtm_send_message(channel, 'Only the current player, *{}*, can take back the last move.'.format(board.current_turn_username), thread)
    board.pop()
    board.save()
    self._render(slack, event, board)

  # triggered by 'chess forfeit'
  def onForfeit(self, slack, args, event):
    """Forfeit the current game."""
    channel, thread = event.channel, event.thread
    board = TarraschBoard.from_backend(channel, thread)
    if board.turn:
      self._handle_game_over(slack, event, board, 'loss')
    else:
      self._handle_game_over(slack, event, board, 'win')

    # triggered by 'chess record'
  def onRecord(self, slack, args, event):
    """Show your record against each of your opponents."""
    channel, thread, user_name = event.channel, event.thread, event.user_name
    record = db.get(user_name)
    if not record:
      return slack.rtm_send_message(channel, 'User *{}* has not played any games.'.format(user_name), thread)
    record = json.loads(str(record))
    table = PrettyTable(['Opponent', 'Games', 'Wins', 'Losses', 'Draws'])
    for opponent, results in record.iteritems():
      table.add_row([opponent, results['win'] + results['loss'] + results['draw'], results['win'], results['loss'], results['draw']])
    table_string = table.get_string(sortby='Games', reversesort=True)
    slack.rtm_send_message(channel, 'Record for *{}*\n```\n{}```'.format(user_name, table_string), thread)

    # triggered by 'chess leaderboard'
  def onLeaderboard(self, slack, args, event):
    """Show the overall W/L/D for all players."""
    channel, thread = event.channel, event.thread
    table = PrettyTable(['Player', 'Games', 'Wins', 'Losses', 'Draws'])
    if db.scard('players') == 0:
      return slack.rtm_send_message(channel, 'No games have been recorded.', thread)
    for player in db.smembers('players'):
      record = db.get(player)
      if not record:
        continue
      record = json.loads(str(record))
      wins, losses, draws = 0, 0, 0
      for opponent, results in record.iteritems():
        wins += results['win']
        losses += results['loss']
        draws += results['draw']
      table.add_row([player, wins + losses + draws, wins, losses, draws])
    table_string = table.get_string(sortby='Wins', reversesort=True)
    slack.rtm_send_message(channel, '```\n{}```'.format(table_string), thread)

    # triggered by 'chess help'
  def onHelp(self, slack, args, event):
    help_string = "I am Xybotsu, the chess bot. My code is on GitHub at xybotsu/chessbot.\n\n"
    for command in sorted(self.COMMANDS.keys()):
      if command == 'help':
          continue
      help_string += '{}: {}\n'.format(command, self.COMMANDS[command].__doc__)
    help_string += '\nYou can read all about algebraic notation here: https://goo.gl/OOquFQ\n'
    slack.rtm_send_message(event.channel, help_string, event.thread)

  def _handle_game_over(self, slack, event, board, result=None):
    channel, thread = event.channel, event.thread
    if not result:
      if board.result() == '1-0':
        result = 'win'
      elif board.result() == '0-1':
        result = 'loss'
      elif board.result() == '*':
        raise ValueError('Result undetermined in game over handler, should not have gotten here')
      else:
        result = 'draw'
    if board.white_user != board.black_user:
      _update_records(board.white_user, board.black_user, result)

    # Upload game for analysis
    try:
      url = upload_analysis(board.get_pgn())
      message = 'This game is available for analysis at {}'.format(url)
    except Exception as e:
      message = 'There was a problem uploading the game for analysis, sorry :anguished:'
    slack.rtm_send_message(channel, message, thread)

    board.kill()
    if result != 'draw':
      winner = board.white_user if result == 'win' else board.black_user
      color = 'white' if result == 'win' else 'black'
      slack.rtm_send_message(channel, '*{}* ({}) wins! Say `{} start` to play another game.'.format(winner, color, MP), thread)
    else:
      slack.rtm_send_message(channel, "It's a draw! Say `{} start` to play another game.".format(MP), thread)

  COMMANDS = {
    'ai': onAi,
    'start': onStart,
    'claim': onClaim,
    'board': onBoard,
    'move': onMove,
    'takeback': onTakeback,
    'forfeit': onForfeit,
    'record': onRecord,
    'leaderboard': onLeaderboard,
    'help': onHelp,
  }

def _humanize(seconds):
  if seconds < 120:
    return '{} seconds'.format(int(round(seconds)))
  elif seconds < 60*60*2:
    return '{} minutes'.format(int(round(seconds/60)))
  elif seconds < 60*60*24:
    return '{} hours'.format(int(round(seconds/(60*60))))
  return '{} days'.format(int(round(seconds/(60*60*24))))

def _update_records(white_user, black_user, result):
  white_result = 'win' if result == 'win' else 'loss'
  black_result = 'loss' if result == 'win' else 'win'
  if result == 'draw':
      white_result, black_result = 'draw', 'draw'
  _update_record(white_user, black_user, white_result)
  _update_record(black_user, white_user, black_result)
  db.sadd('players', white_user)
  db.sadd('players', black_user)

def _update_record(user, against, result):
  record = json.loads(str(db.get(user) or {}))
  if against not in record:
    record[against] = {'win': 0, 'loss': 0, 'draw': 0}
  record[against][result] += 1
  db.set(user, json.dumps(record))
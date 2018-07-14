from slackclient import SlackClient
from .config import SLACK_TOKEN
import time

USER_CACHE = {}

slack = SlackClient(SLACK_TOKEN)

# store a cache of userId -> userName mappings, so we don't need to make API calls every time
def _getUser(user_id):
  if not USER_CACHE.get(user_id):
    USER_CACHE[user_id] = slack.api_call('users.info', user=user_id)['user']
  return USER_CACHE[user_id]

def _isMessageLike(event):
    return event.type == 'message' and event.subtype is None and event.text is not None

def threadedMessageEvents(event):
    return _isMessageLike(event) and event.thread_ts is not None

def messageEvents(event):
    return _isMessageLike(event) and event.thread_ts is None

def allEvents(e): return e

class MaybeCallback(object):
  def __init__(self, callback, predicate):
    self.callback = callback
    self.predicate = predicate

class Xybotsu(object):

  def __init__(self, slack):
    self.slack = slack
    if (not self.slack.rtm_connect()): raise IOError('Connection to Slack failed, check your token')
    self.callbacks = {}

  # listens for commands, and process them in turn
  def listen(self):
    while True:
      events = filter(lambda e: e.get('type') == 'message' and 'text' in e, self.slack.rtm_read())
      for event in events:
        command = messageEventToCommand(event)
        if command:
          self.notify(command) # notifies all listeners
      time.sleep(0.5)

  # store a dict from command -> maybeCallback
  def register(self, command, callback, condition):
    maybeCallback = MaybeCallback(callback, condition)
    if self.callbacks.get(command):
      self.callbacks[command].append(maybeCallback)
    else:
      self.callbacks[command] = [maybeCallback]

  # notifies all subscribers when command triggers
  def notify(self, command):
    for mc in (self.callbacks.get(command.name) or []):
      if mc.predicate(command.event):
        mc.callback(self.slack, command.args, command.event)

def isMessage(event):
  return event.get('type') == 'message' and 'subtype' not in event and 'text' in event

class Command(object):
  def __init__(self, args, event):
    self.args = args
    self.event = event

  def log(self):
    print("{args} {event}".format(args=self.args, event=self.event))

class ChessAi(Command):
  name = 'chess ai'

class ChessStart(Command):
  name = 'chess start'

class ChessClaim(Command):
  name = 'chess claim'

class ChessForfeit(Command):
  name = 'chess forfeit'

class ChessMove(Command):
  name = 'chess move'

class ChessHelp(Command):
  name = 'chess help'

class ChessBoard(Command):
  name = 'chess board'

class ChessTakeback(Command):
  name = 'chess takeback'

class ChessRecord(Command):
  name = 'chess board'

class ChessLeaderboard(Command):
  name = 'chess board'

class Event(object):
  def __init__(self, type, subtype, channel, user_id, text, ts, thread_ts):
    self.type = type
    self.subtype = subtype
    self.channel = channel
    self.user_id = user_id
    self.user_name = _getUser(user_id)['name']
    self.text = text
    self.ts = ts
    self.thread_ts = thread_ts

def messageEventToCommand(event):
  commands = {
    'chess ai': ChessAi,
    'chess start': ChessStart,
    'chess claim': ChessClaim,
    'chess board': ChessBoard,
    'chess move': ChessMove,
    'chess takeback': ChessTakeback,
    'chess forfeit': ChessForfeit,
    'chess record': ChessRecord,
    'chess leaderboard': ChessLeaderboard,
    'chess help': ChessHelp,
  }

  for command in commands.keys():
    if event['text'].startswith(command):
      args = event['text'][len(command):].strip().split()
      return commands[command](
        args,
        Event(
          event.get('type'),
          event.get('subtype'),
          event.get('channel'),
          event.get('user'),
          event.get('text'),
          event.get('ts'),
          event.get('thread_ts')
        )
      )

  return None


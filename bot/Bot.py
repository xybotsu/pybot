from dataclasses import dataclass
from typing import Dict, List
from redis import from_url, StrictRedis
from .config import SLACK_TOKEN
from slackclient import SlackClient
import time


slack = SlackClient(SLACK_TOKEN)


class Bot(object):

    def __init__(self, slack):
        self.slack = slack
        if (not self.slack.rtm_connect()):
            raise IOError('Connection to Slack failed, check your token')
        self._triggers = {}

    def register(self, trigger, callback, condition):
        # registers a trigger, which fires a callback if condition is true
        maybeCallback = _MaybeCallback(callback, condition)
        self._triggers.setdefault(trigger, [maybeCallback])

    def notify(self, command):
        # notifies all subscribers when command triggers, if condition is true
        for mc in (self._triggers.get(command.trigger, [])):
            if mc.condition(command.event):
                mc.callback(self.slack, command)

    def listen(self):
        # listens for commands, and process them in turn
        while True:
            events = filter(lambda e: e.get('type') ==
                            'message' and 'text' in e, self.slack.rtm_read())
            for event in events:
                command = self._messageEventToCommand(event)
                if command:
                    self.notify(command)  # notifies all listeners
            time.sleep(0.5)

    def _messageEventToCommand(self, event):
        for trigger in self._triggers.keys():
            if event['text'].startswith(trigger):
                args = event['text'][len(trigger):].strip().split()
                return Command(
                    trigger,
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


@dataclass
class Command:
    trigger: str
    args: List[str]
    event: object

    @property
    def user_name(self) -> str:
        return _getUser(self.event.user_id)['name']

    @property
    def channel(self) -> str:
        return self.event.channel

    @property
    def thread(self) -> str:
        return self.event.thread

    def log(self):
        print("{trigger} {args} {event}".format(
            trigger=self.trigger, args=self.args, event=self.event)
        )


@dataclass
class Event:
    type: str
    subtype: str
    channel: str
    user_id: str
    text: str
    ts: str
    thread: str


def threadedMessageEvents(event):
    return _isMessageLike(event) and event.thread is not None


def messageEvents(event):
    return _isMessageLike(event) and event.thread is None


_USER_CACHE: Dict[str, object] = {}


def _getUser(user_id):
    # store a cache of userId -> userName mappings,
    # so we don't need to make API calls every time
    if not _USER_CACHE.get(user_id):
        _USER_CACHE[user_id] = slack.api_call(
            'users.info', user=user_id)['user']
    return _USER_CACHE[user_id]


def _isMessageLike(event):
    return (
        event.type == 'message' and
        event.subtype is None and
        event.text is not None
    )


class _MaybeCallback(object):
    def __init__(self, callback, condition):
        self.callback = callback
        self.condition = condition

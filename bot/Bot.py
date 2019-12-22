from dataclasses import dataclass
from typing import Callable, Dict, List, Optional
from redis import from_url, StrictRedis
from .config import SLACK_TOKEN
from .users import getUser
import time
from slackclient import SlackClient


@dataclass
class Bot:
    name: str
    icon_emoji: str


class SlackBot(SlackClient):

    def __init__(self, token: str, bot: Bot, db: StrictRedis) -> None:
        super().__init__(token)
        if (not self.rtm_connect()):
            raise IOError('Connection to Slack failed, check your token')
        self.bot = bot
        self.db = db
        self._triggers: Dict = {}

    def postMessage(self, channel: str, message: str, thread: Optional[str]):
        self.api_call(
            'chat.postMessage',
            channel=channel,
            text=message,
            thread_ts=thread,
            username=self.bot.name,
            icon_emoji=self.bot.icon_emoji
        )

    def register(self, trigger: str, callback, condition):
        # registers a trigger, which fires a callback if condition is true
        maybeCallback = _MaybeCallback(callback, condition)
        self._triggers.setdefault(trigger, [maybeCallback])

    def notify(self, command):
        # notifies all subscribers when command triggers, if condition is true
        for mc in (self._triggers.get(command.trigger, [])):
            if mc.condition(command.event):
                mc.callback(command)

    def listen(self):
        # listens for commands, and process them in turn
        while True:
            try:
                events = filter(lambda e: e.get('type') ==
                                'message' and 'text' in e, self.rtm_read())
                for event in events:
                    command = self._messageEventToCommand(event)
                    if command:
                        self.notify(command)  # notifies all listeners
                time.sleep(0.5)
            except Exception as e:
                print(e)
                print("Websocket error. Reconnecting!")
                self.rtm_connect()

    def _messageEventToCommand(self, event):
        for trigger in self._triggers.keys():
            if event['text'].lower().startswith(trigger.lower()):
                args = event['text'][len(trigger):].strip().lower().split()
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
class Event:
    type: str
    subtype: str
    channel: str
    user_id: str
    text: str
    ts: str
    thread: str


@dataclass
class Command:
    trigger: str
    args: List[str]
    event: Event

    @property
    def user_name(self) -> str:
        return getUser(self.event.user_id)['name']

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


def threaded(event):
    return allMessageEvents(event) and event.thread is not None


def messageEvents(event):
    return allMessageEvents(event) and event.thread is None


def allMessageEvents(event):
    return (
        event.type == 'message' and
        event.subtype is None and
        event.text is not None
    )


class _MaybeCallback(object):
    def __init__(self, callback, condition):
        self.callback = callback
        self.condition = condition

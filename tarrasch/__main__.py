import json
import time
import logging

from slackclient import SlackClient

from .config import SLACK_TOKEN, MESSAGE_PREFIX
from .handler import handle_message

USER_CACHE = {}

def _ensure_cached_user_info(client, event):
    user_id = event.get('user')
    if user_id in USER_CACHE or not user_id:
        return
    USER_CACHE[user_id] = client.api_call('users.info', user=user_id)['user']

def _isMessageLike(event):
    return event.get('type') == 'message' and 'subtype' not in event and 'text' in event

def _isThreadedMessageEvent(event):
    return _isMessageLike(event) and 'thread_ts' in event

def _isMessageEvent(event):
    return _isMessageLike(event) and 'thread_ts' not in event

def _route_event(client, event):
    _ensure_cached_user_info(client, event)
    if _isThreadedMessageEvent(event):
        if event['text'].lower().startswith(MESSAGE_PREFIX.lower()):
            channel = event['channel']
            message = event['text'][len(MESSAGE_PREFIX):].strip()
            thread = event['thread_ts']
            user_name = USER_CACHE[event['user']]['name']
            if message:
                handle_message(client, channel, thread, user_name, message)

    elif _isMessageEvent(event):
        if event['text'].lower().startswith(MESSAGE_PREFIX.lower()):
            channel = event['channel']
            message = event['text'][len(MESSAGE_PREFIX):].strip()
            user_name = USER_CACHE[event['user']]['name']
            if message:
                client.rtm_send_message(channel, '`chess <command>` must be run inside a thread!')

def main():
    client = SlackClient(SLACK_TOKEN)
    if (not client.rtm_connect()): raise IOError('Connection to Slack failed, check your token')
    while True:
        events = client.rtm_read()
        if events:
            for event in events:
                _route_event(client, event)
        else:
            time.sleep(0.5)

if __name__ == '__main__':
    try:
        main()
    except Exception as e: # die on any other error
        logging.exception('Error bubbled up to main loop')

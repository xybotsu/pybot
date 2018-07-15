import random
import pickle
import datetime

from chess import Board, SQUARES_180, pgn

from .database import singleton as db
from .shortener import shorten_url


class TarraschNoBoardException(Exception):
    pass


class TarraschBoard(Board):
    """An augmented Board from python-chess which also knows
    how to do useful things like persist itself, build itself
    from its persistence layer, render itself using jinchess diagrams,
    all sorts of fun stuff."""

    def __init__(self, channel, thread, white_user, black_user, *args,
                 **kwargs):
        super(TarraschBoard, self).__init__(*args, **kwargs)
        self.channel = channel
        self.thread = thread
        self.white_user = white_user
        self.black_user = black_user
        self.last_move_time = 0

    @staticmethod
    def getDbKey(channel, thread):
        return channel + '-' + thread

    @classmethod
    def from_backend(cls, channel, thread):
        """Return the saved TarraschBoard for the given channel + thread, or
        raise a TarraschNoBoardException if there is none."""
        record = db.get(TarraschBoard.getDbKey(channel, thread))
        if not record:
            raise TarraschNoBoardException(
                'No board found for channel {}, thread {}'
                .format(channel, thread))
        payload = pickle.loads(record)
        board = cls(channel, thread,
                    payload['white_user'], payload['black_user'])
        board.last_move_time = payload['last_move_time'] or 0
        # Restore board positions from FEN
        board.set_fen(payload['fen'])
        # Restore state variables
        board.move_stack = payload['move_stack']
        board.stack = payload['stack']
        return board

    def save(self, last_move_time=None):
        payload = {
            'fen': self.fen(),
            'white_user': self.white_user,
            'black_user': self.black_user,
            'last_move_time': last_move_time,
            'move_stack': self.move_stack,
            'stack': self.stack
        }
        db.set(self._getDbKey(), pickle.dumps(payload))

    def _getDbKey(self):
        return TarraschBoard.getDbKey(self.channel, self.thread)

    def kill(self):
        db.delete(self._getDbKey())

    def get_url(self, shorten=False):
        render_string = ''
        for square in SQUARES_180:
            piece = self.piece_at(square)
            if piece:
                render_string += piece.symbol()
            else:
                render_string += '-'
        # We add some noise at the end to force Slack to render our shit
        url = 'http://www.jinchess.com/chessboard/' \
            + '?s=s&cm=r&ps=alpha-flat&p={}#{}'.format(
                render_string, random.randint(0, 10000000))
        if shorten:
            url = shorten_url(url)
        return url

    @property
    def current_turn_username(self):
        return self.white_user if self.turn else self.black_user

    def get_pgn(self):
        """Returns a string representing the PGN for the current board state (and
        the moves leading up to it)."""
        root = pgn.Game()
        root.headers['Event'] = 'Tarrasch Chess Bot'
        root.headers['Date'] = datetime.datetime.utcnow().strftime('%Y.%m.%d')
        root.headers['White'] = self.white_user
        root.headers['Black'] = self.black_user

        next = root
        for move in self.move_stack:
            next = next.add_main_variation(move)

        return root.__str__()

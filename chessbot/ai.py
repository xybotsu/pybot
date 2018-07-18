import chess
from random import choice

board = chess.Board()


def getMove(board):
    # Todo: replace this with a smarter AI
    return choice(
        list(board.legal_moves)
    )

import chess
from random import choice
from chess import Board, Move

board = chess.Board()


def getMove(board: Board) -> Move:
    # Todo: replace this with a smarter AI
    return choice(list(board.legal_moves))

from bot.Bot import SlackBot, Command
from .ai import getMove
from .analysis import upload_analysis
from .board import TarraschBoard, TarraschNoBoardException
from chess import SQUARE_NAMES
from prettytable import PrettyTable

import json
import time

COOLDOWN_SECONDS = 0
MP = "chess"


class ChessBot(SlackBot):
    def __init__(self, token, bot, db):
        super().__init__(token, bot, db)
        self.STARTUP_STATE = {}

    def onStart(self, cmd: Command):
        """Start a new game."""
        channel, thread = cmd.channel, cmd.thread
        try:
            board = TarraschBoard.from_backend(channel, thread)
        except TarraschNoBoardException:
            board = None

        if board:
            return self.postMessage(
                channel,
                "A game is already going on in this channel between {} and {}".format(
                    board.white_user, board.black_user
                ),
                thread,
            )
        self.STARTUP_STATE[TarraschBoard.getDbKey(channel, thread)] = {}
        self.postMessage(
            channel,
            (
                "Let's play chess! I need two players to say"
                + "{0} claim white or `{0} claim black`."
            ).format(MP),
            thread,
        )

    def onClaim(self, cmd: Command):
        """Claim a side in the next game. Used after a start command."""
        args, channel, thread, user_name = (
            cmd.args,
            cmd.channel,
            cmd.thread,
            cmd.user_name,
        )
        if TarraschBoard.getDbKey(channel, thread) not in self.STARTUP_STATE:
            return self.postMessage(
                channel, "Say `{} start` to start a new game.".format(MP), thread
            )

        color = args[0].lower()
        ai = args[1] if len(args) > 1 else None  # claim black kasparov
        if color not in ["white", "black"]:
            return self.postMessage(
                channel,
                (
                    "Say `{} claim white` or `{} claim black [ai]`"
                    + " to pick your side."
                ).format(MP, MP),
                thread,
            )

        # todo: fix architecture
        if ai == "kasparov":
            user_name = "kasparov"

        self.STARTUP_STATE[TarraschBoard.getDbKey(channel, thread)][color] = user_name
        self.postMessage(
            channel, "*{}* will play as {}.".format(user_name, color), thread
        )

        if (
            "white" in self.STARTUP_STATE[TarraschBoard.getDbKey(channel, thread)]
            and "black" in self.STARTUP_STATE[TarraschBoard.getDbKey(channel, thread)]
        ):
            self._start_game(
                cmd,
                self.STARTUP_STATE[TarraschBoard.getDbKey(channel, thread)]["white"],
                self.STARTUP_STATE[TarraschBoard.getDbKey(channel, thread)]["black"],
            )
            del self.STARTUP_STATE[TarraschBoard.getDbKey(channel, thread)]

    def _start_game(self, cmd: Command, white_user: str, black_user: str):
        channel, thread = cmd.channel, cmd.thread
        board = TarraschBoard(channel, thread, white_user, black_user)
        board.save()
        self._render(cmd, board)

    def _render(self, cmd: Command, board=None):
        channel, thread = cmd.channel, cmd.thread
        if not board:
            board = TarraschBoard.from_backend(channel, thread)
        self.postMessage(channel, board.get_url(shorten=True), thread)
        color = "white" if board.turn else "black"
        user = board.white_user if color == "white" else board.black_user
        if not board.is_game_over():
            message = ""
            if board.move_stack:
                last_move = board.move_stack[-1]
                from_square, to_square = (
                    SQUARE_NAMES[last_move.from_square],
                    SQUARE_NAMES[last_move.to_square],
                )
                message += "Last move: {} → {}. ".format(from_square, to_square)
            message += "*{}* ({}) to play.".format(user, color)
            if board.is_check():
                message += " Check."
            self.postMessage(channel, message, thread)

    def onBoard(self, cmd: Command):
        """Show the current board state for the game in this channel."""
        self._render(cmd)

    def onMove(self, cmd: Command):
        """Make a new move. Use algebraic notation, e.g. `move Nc3`"""
        args, channel, thread, user_name = (
            cmd.args,
            cmd.channel,
            cmd.thread,
            cmd.user_name,
        )
        board = TarraschBoard.from_backend(channel, thread)
        if user_name != board.current_turn_username:  # not this person's turn
            return
        if len(args) == 0:
            return
        time_until_can_move = COOLDOWN_SECONDS - (time.time() - board.last_move_time)
        if time_until_can_move > 1:
            return self.postMessage(
                channel,
                "You must wait {} to make a move.".format(
                    _humanize(time_until_can_move)
                ),
                thread,
            )

        move = args[0]
        try:
            board.push_san(move)
            if board.black_user == "kasparov":
                board.push(getMove(board))
        except ValueError as e:
            msg = (
                f"The move {move} is illegal: {e}\nLegal moves are: {board.legal_moves}"
            )
            return self.postMessage(channel, msg, thread)
        board.save(last_move_time=time.time())
        self._render(cmd, board=board)
        if board.is_game_over():
            self._handle_game_over(cmd, board)

    def onTakeback(self, cmd: Command):
        """Take back the last move. Can only be done by the current player."""
        channel, thread, user_name = (cmd.channel, cmd.thread, cmd.user_name)
        board = TarraschBoard.from_backend(channel, thread)
        if user_name != board.current_turn_username:
            return self.postMessage(
                channel,
                "Only the current player, *{}*, can take back the last move.".format(
                    board.current_turn_username
                ),
                thread,
            )
        board.pop()
        board.save()
        self._render(cmd, board)

    def onForfeit(self, cmd: Command):
        """Forfeit the current game."""
        channel, thread = cmd.channel, cmd.thread
        board = TarraschBoard.from_backend(channel, thread)
        if board.turn:
            self._handle_game_over(cmd, board, "loss")
        else:
            self._handle_game_over(cmd, board, "win")

    def onRecord(self, cmd: Command):
        """Show your record against each of your opponents."""
        channel, thread, user_name = (cmd.channel, cmd.thread, cmd.user_name)
        record = self.db.get(user_name)
        if not record:
            return self.postMessage(
                channel, "User *{}* has not played any games.".format(user_name), thread
            )
        record = json.loads(str(record))
        table = PrettyTable(["Opponent", "Games", "Wins", "Losses", "Draws"])
        for opponent, results in record.iteritems():
            table.add_row(
                [
                    opponent,
                    results["win"] + results["loss"] + results["draw"],
                    results["win"],
                    results["loss"],
                    results["draw"],
                ]
            )
        table_string = table.get_string(sortby="Games", reversesort=True)
        self.postMessage(
            channel,
            "Record for *{}*\n```\n{}```".format(user_name, table_string),
            thread,
        )

    def onLeaderboard(self, cmd: Command):
        """Show the overall W/L/D for all players."""
        channel, thread = cmd.channel, cmd.thread
        table = PrettyTable(["Player", "Games", "Wins", "Losses", "Draws"])
        if self.db.scard("players") == 0:
            return self.postMessage(channel, "No games have been recorded.", thread)
        for player in self.db.smembers("players"):
            record = self.db.get(player)
            if not record:
                continue
            record = json.loads(str(record))
            wins, losses, draws = 0, 0, 0
            for _, results in record.iteritems():
                wins += results["win"]
                losses += results["loss"]
                draws += results["draw"]
            table.add_row([player, wins + losses + draws, wins, losses, draws])
        table_string = table.get_string(sortby="Wins", reversesort=True)
        self.postMessage(channel, "```\n{}```".format(table_string), thread)

    def onHelp(self, cmd: Command):
        if cmd.thread is None:
            self.postMessage(
                cmd.channel,
                "Chess commands can only be run inside slack threads!",
                cmd.thread,
            )
            return

        help_string = (
            "Let's play some chess. " + "My code is on GitHub at xybotsu/chessbot.\n\n"
        )
        channel, thread = cmd.channel, cmd.thread
        for command in sorted(self.COMMANDS.keys()):
            if command == "help":
                continue
            help_string += "{}: {}\n".format(command, self.COMMANDS[command].__doc__)
        help_string += '\nYou can read all about algebraic " + \
            "notation here: https://goo.gl/OOquFQ\n'
        self.postMessage(channel, help_string, thread)

    def _update_records(self, white_user: str, black_user: str, result: str):
        white_result = "win" if result == "win" else "loss"
        black_result = "loss" if result == "win" else "win"
        if result == "draw":
            white_result, black_result = "draw", "draw"
        self._update_record(white_user, black_user, white_result)
        self._update_record(black_user, white_user, black_result)
        self.db.sadd("players", white_user)
        self.db.sadd("players", black_user)

    def _update_record(self, user, against, result):
        record = json.loads(str(self.db.get(user) or {}))
        if against not in record:
            record[against] = {"win": 0, "loss": 0, "draw": 0}
        record[against][result] += 1
        self.db.set(user, json.dumps(record))

    def _handle_game_over(self, cmd: Command, board, result=None):
        channel, thread = cmd.channel, cmd.thread
        if not result:
            if board.result() == "1-0":
                result = "win"
            elif board.result() == "0-1":
                result = "loss"
            elif board.result() == "*":
                raise ValueError(
                    "Result undetermined in game over handler,"
                    + " should not have gotten here"
                )
            else:
                result = "draw"
        if board.white_user != board.black_user:
            self._update_records(board.white_user, board.black_user, result)

        # Upload game for analysis
        try:
            url = upload_analysis(board.get_pgn())
            message = "This game is available for analysis at {}".format(url)
        except Exception:
            message = "There was a problem uploading the game!"
        self.postMessage(channel, message, thread)

        board.kill()
        if result != "draw":
            winner = board.white_user if result == "win" else board.black_user
            color = "white" if result == "win" else "black"
            self.postMessage(
                channel,
                "*{}* ({}) wins! Say `{} start` to play another game.".format(
                    winner, color, MP
                ),
                thread,
            )
        else:
            self.postMessage(
                channel,
                "It's a draw! Say `{} start` to play another game.".format(MP),
                thread,
            )

    COMMANDS = {
        "start": onStart,
        "claim": onClaim,
        "board": onBoard,
        "move": onMove,
        "takeback": onTakeback,
        "forfeit": onForfeit,
        "record": onRecord,
        "leaderboard": onLeaderboard,
        "help": onHelp,
    }


def _humanize(seconds: int) -> str:
    if seconds < 120:
        return "{} seconds".format(int(round(seconds)))
    elif seconds < 60 * 60 * 2:
        return "{} minutes".format(int(round(seconds / 60)))
    elif seconds < 60 * 60 * 24:
        return "{} hours".format(int(round(seconds / (60 * 60))))
    return "{} days".format(int(round(seconds / (60 * 60 * 24))))

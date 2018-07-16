### Xybotsu Slack Chessbot

![](https://i.imgur.com/GdGnKBh.png)

### What is this?
Challenge your buddies to a chess match inside Slack! Keeps track of a leaderboard of wins and losses, and automatically uploads each game to lichess.org for analysis.

### Credit
Forked from https://github.com/thieman/tarrasch with the following changes:
- Games are played inside of slack threads. This is done to avoid cluttering an entire channel, and to allow multiple games to progress simultaneously within one channel.
- Uses the latest version of python-chess (currently at 0.23.9)
- Decoupled the command layer from the game logic
- Play against an AI opponent collaboratively with friends (work in progress)

### Full List of Commands
```
chess start
chess claim
chess board
chess move
chess takeback
chess forfeit
chess record
chess leaderboard
chess help
```
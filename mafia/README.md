# Mafia Package

This package contains the core game engine and related utilities.

* `game.py` – coordinates day and night cycles and emits structured events.
* `events.py` – tiny publish/subscribe dispatcher used by the game.
* `logger.py` – default logger subscribing to game events.
* `actions.py`, `player.py`, `roles.py` – fundamental game data structures.
* `simulate.py` – helpers for running batches of games.

The event system allows custom observers and loggers to be attached without
modifying the engine.  See the project root `README.md` for an overview and
examples.

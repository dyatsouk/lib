# Mafia Package

This package contains the core game engine and related utilities.

* `game.py` – coordinates day and night cycles and emits structured events.
* `events.py` – tiny publish/subscribe dispatcher used by the game.
* `logger.py` – default logger subscribing to game events.
* `actions.py`, `player.py`, `roles.py` – fundamental game data structures. Role
  classes expose ``perform_night_action`` hooks implemented by small behaviour
  classes so the engine can trigger actions without knowing about concrete
  role types.
* `simulate.py` – helpers for running batches of games.

The event system allows custom observers and loggers to be attached without
modifying the engine.  See the project root `README.md` for an overview and
examples.

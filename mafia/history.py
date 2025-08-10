"""Persistence helpers for storing full game histories.

The :mod:`mafia.history` module provides :class:`GameHistoryDB` – a thin
wrapper around an SQLite database used to persist the full history of played
games.  To improve throughput the database layer now buffers inserts and
commits them in batches.  The batch size is configurable: larger batches reduce
``COMMIT`` overhead but increase the risk of losing the most recent games if
the process terminates unexpectedly before the buffer is flushed.
"""

import json
import sqlite3
from dataclasses import asdict
from pathlib import Path
from typing import List, Tuple

from .game import Game
from .roles import Role


class GameHistoryDB:
    """SQLite-backed storage for full game histories.

    Parameters
    ----------
    path:
        Location of the SQLite database file.  A new file is created when the
        path does not already exist.
    batch_size:
        Number of games to buffer before committing them to disk.  Setting this
        to ``1`` (the default) preserves the previous behaviour of committing
        each game immediately.  Higher values improve logging speed at the cost
        of durability – a crash may lose the last incomplete batch.
    """

    def __init__(self, path: str | Path = "games.db", *, batch_size: int = 1):
        self.path = Path(path)
        self.conn = sqlite3.connect(self.path)
        # ``batch_size`` controls how many games are inserted in one transaction.
        self.batch_size = batch_size
        # Internal buffer collecting uncommitted game rows.
        self._buffer: List[Tuple[str, str]] = []
        self._init_schema()

    def _init_schema(self) -> None:
        cur = self.conn.cursor()
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS games (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                winner TEXT NOT NULL,
                history TEXT NOT NULL
            )
            """
        )
        self.conn.commit()

    def log_game(self, game: Game, winner: Role) -> None:
        """Persist the raw game data as JSON.

        The game is appended to the internal buffer and written to disk once the
        configured ``batch_size`` is reached.  Flushing the buffer is handled
        automatically when the object is closed.
        """

        data = {
            "players": [p.role.name for p in game.players],
            "rounds": [asdict(r) for r in game.history],
        }
        # Accumulate rows in memory first so that multiple inserts can be
        # committed in a single transaction.
        self._buffer.append((winner.name, json.dumps(data)))
        if len(self._buffer) >= self.batch_size:
            self._commit_batch()

    def _commit_batch(self) -> None:
        """Commit all buffered game rows in a single transaction."""

        if not self._buffer:
            return
        # ``with self.conn`` opens a transaction and commits on success,
        # rolling back automatically if an exception is raised.
        with self.conn:
            self.conn.executemany(
                "INSERT INTO games (winner, history) VALUES (?, ?)",
                self._buffer,
            )
        self._buffer.clear()

    def close(self) -> None:
        """Flush any pending rows and close the underlying database connection."""

        # Ensure any remaining buffered games are persisted before closing.
        self._commit_batch()
        self.conn.close()

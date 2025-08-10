import json
import sqlite3
from dataclasses import asdict
from pathlib import Path

from .game import Game
from .roles import Role


class GameHistoryDB:
    """SQLite-backed storage for full game histories."""

    def __init__(self, path: str | Path = "games.db"):
        self.path = Path(path)
        self.conn = sqlite3.connect(self.path)
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
        """Persist the raw game data as JSON."""

        data = {
            "players": [p.role.name for p in game.players],
            "rounds": [asdict(r) for r in game.history],
        }
        cur = self.conn.cursor()
        cur.execute(
            "INSERT INTO games (winner, history) VALUES (?, ?)",
            (winner.name, json.dumps(data)),
        )
        self.conn.commit()

    def close(self) -> None:
        self.conn.close()

from types import SimpleNamespace
import sys
from pathlib import Path
import sqlite3

sys.path.append(str(Path(__file__).resolve().parents[1]))

from mafia.actions import DayLog, NightLog, RoundLog, SpeechAction, SpeechLog
from mafia.history import GameHistoryDB
from mafia.roles import Role


def _make_game(nominations: int, kill: bool, elimination: bool):
    """Create a minimal game object with specified counts."""

    players = [SimpleNamespace(role=Role.CIVILIAN), SimpleNamespace(role=Role.MAFIA)]

    speeches = [
        SpeechLog(speaker=0, action=SpeechAction(nomination=1))
        for _ in range(nominations)
    ]
    day = DayLog(speeches=speeches, votes=[], eliminated=[1] if elimination else None)
    night = NightLog(
        sheriff_check=None, don_check=None, kill=0 if kill else None
    )
    history = [RoundLog(day=day, night=night)]
    return SimpleNamespace(players=players, history=history)


def test_history_totals(tmp_path):
    """Aggregated counts in the database match the original games."""

    games = [
        _make_game(1, True, True),
        _make_game(2, False, True),
        _make_game(0, True, False),
        _make_game(3, True, True),
        _make_game(1, False, False),
    ]

    expected_noms = sum(
        1
        for g in games
        for r in g.history
        for s in r.day.speeches
        if s.action.nomination is not None
    )
    expected_kills = sum(
        1
        for g in games
        for r in g.history
        if r.night and r.night.kill is not None
    )
    expected_elims = sum(
        1
        for g in games
        for r in g.history
        if r.day.eliminated is not None
    )

    db_path = tmp_path / "games.db"
    db = GameHistoryDB(db_path)
    for game in games:
        db.log_game(game, Role.CIVILIAN)

    cur = db.conn.cursor()

    cur.execute(
        """
        SELECT SUM(json_extract(s.value, '$.action.nomination') IS NOT NULL)
        FROM games g,
             json_each(g.history, '$.rounds') AS r,
             json_each(json_extract(g.history, '$.rounds[' || r.key || '].day.speeches')) AS s
        """
    )
    db_noms = cur.fetchone()[0]

    cur.execute(
        """
        SELECT SUM(json_extract(r.value, '$.night.kill') IS NOT NULL)
        FROM games g, json_each(g.history, '$.rounds') AS r
        """
    )
    db_kills = cur.fetchone()[0]

    cur.execute(
        """
        SELECT SUM(json_extract(r.value, '$.day.eliminated') IS NOT NULL)
        FROM games g, json_each(g.history, '$.rounds') AS r
        """
    )
    db_elims = cur.fetchone()[0]

    db.close()

    assert db_noms == expected_noms
    assert db_kills == expected_kills
    assert db_elims == expected_elims


def test_batched_logging(tmp_path):
    """Games are buffered and committed in batches without data loss."""

    games = [_make_game(1, True, False) for _ in range(5)]
    db_path = tmp_path / "games.db"
    db = GameHistoryDB(db_path, batch_size=2)

    # Insert games and monitor how the on-disk row count changes. The count
    # should only increase when the batch size is reached.
    for idx, game in enumerate(games, start=1):
        db.log_game(game, Role.CIVILIAN)
        conn = sqlite3.connect(db_path)
        row_count = conn.execute("SELECT COUNT(*) FROM games").fetchone()[0]
        conn.close()
        if idx % 2 == 0:
            assert row_count == idx
        else:
            assert row_count == idx - 1

    # Closing the DB flushes the final partial batch.
    db.close()
    conn = sqlite3.connect(db_path)
    final_count = conn.execute("SELECT COUNT(*) FROM games").fetchone()[0]
    conn.close()
    assert final_count == len(games)


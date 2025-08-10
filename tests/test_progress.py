"""Tests ensuring progress bars are wired into simulation and optimisation."""

from mafia import simulate, optimization
from mafia.roles import Role
from mafia.strategies import CivilianStrategy


def test_simulate_games_uses_tqdm(monkeypatch):
    """Ensure :func:`simulate.simulate_games` delegates to ``tqdm``."""

    calls = {}

    def fake_tqdm(iterable, **kwargs):
        calls['total'] = len(iterable)
        return iterable

    monkeypatch.setattr(simulate, 'tqdm', fake_tqdm)
    simulate.simulate_games(1)
    assert calls['total'] == 1


def test_optimise_all_uses_tqdm(monkeypatch):
    """Verify optimisation wraps the total round count in ``tqdm``."""

    progress = {'total': 0, 'updates': 0}

    class DummyBar:
        """Minimal context manager mimicking :class:`tqdm`'s API."""

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            pass

        def update(self, n=1):
            progress['updates'] += n

    def fake_tqdm(total, **kwargs):
        progress['total'] = total
        return DummyBar()

    # Patch tqdm in both optimisation and simulation to avoid real progress output
    monkeypatch.setattr(optimization, 'tqdm', fake_tqdm)
    monkeypatch.setattr(simulate, 'tqdm', lambda iterable, **_: iterable)

    params = {Role.CIVILIAN: (CivilianStrategy, {'nomination_prob': 0.3})}
    optimization.optimise_all(params, rounds=2, games=1, seed=0)

    assert progress['total'] == 2
    assert progress['updates'] == 2


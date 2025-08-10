"""Tests for optimisation helpers.

The optimisation routines simulate games to tweak strategy parameters.  These
tests exercise both the single-parameter helper and the multi-role optimisation
to ensure they return reasonable win rates and updated values.
"""

import random
from mafia.roles import Role
from mafia.strategies import CivilianStrategy, MafiaStrategy, DonStrategy, SheriffStrategy
from mafia.optimization import optimise_parameter, optimise_all


def test_optimise_parameter_reduces_nomination_prob():
    """Hill-climb should decrease nomination probability for civilians."""

    # Fix the strategies for other roles so only the Civilian parameter varies.
    base_config = {
        Role.MAFIA: (MafiaStrategy, {"nomination_prob": 0.3}),
        Role.DON: (DonStrategy, {"nomination_prob": 0.3}),
        Role.SHERIFF: (SheriffStrategy, {"reveal_prob": 1.0, "nomination_prob": 0.3}),
    }

    # Start the civil nomination probability high and let the optimiser adjust
    # it; we expect a reduction since nominating randomly hurts civilians.
    res = optimise_parameter(
        Role.CIVILIAN,
        CivilianStrategy,
        "nomination_prob",
        0.4,
        step=0.1,
        games=20,
        iterations=2,
        target=Role.CIVILIAN,
        base_config=base_config,
        seed=0,
    )

    # The returned value should be lower than the starting point and produce a
    # sensible win rate within [0, 1].
    assert res.value < 0.4
    assert 0 <= res.win_rate <= 1


def test_optimise_all_returns_results():
    """Optimising multiple roles should return a result for each."""

    # Describe the parameters to optimise for each role.  Each tuple contains
    # the strategy class, the parameter name, and the starting value.
    params = {
        Role.CIVILIAN: (CivilianStrategy, "nomination_prob", 0.3),
        Role.MAFIA: (MafiaStrategy, "nomination_prob", 0.3),
    }

    # Run a single coordinate-descent round with a small number of games to
    # keep the test fast.
    results = optimise_all(
        params,
        step=0.1,
        games=10,
        rounds=1,
        target=Role.CIVILIAN,
        seed=0,
    )

    # Ensure we get an OptimisationResult for each role and that win rates are
    # valid probabilities.
    assert set(results) == {Role.CIVILIAN, Role.MAFIA}
    assert all(0 <= r.win_rate <= 1 for r in results.values())

"""Tests for optimisation helpers.

The optimisation routines simulate games to tweak strategy parameters. These
tests exercise both the single-parameter helper and the multi-role optimisation
to ensure they return reasonable win rates and updated values.
"""

from pathlib import Path

from mafia.roles import Role
from mafia.strategies import CivilianStrategy, MafiaStrategy, DonStrategy, SheriffStrategy
from mafia.optimization import optimise_parameter, optimise_all, optimise_from_config


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
    # the strategy class and a mapping of parameter names to start values.
    params = {
        Role.CIVILIAN: (CivilianStrategy, {"nomination_prob": 0.3}),
        Role.MAFIA: (MafiaStrategy, {"nomination_prob": 0.3}),
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
    assert all(
        0 <= r.win_rate <= 1
        for role_results in results.values()
        for r in role_results.values()
    )


def test_optimise_all_handles_multiple_params():
    """A single role with multiple parameters should yield results for each."""

    params = {
        Role.SHERIFF: (
            SheriffStrategy,
            {"nomination_prob": 0.3, "reveal_prob": 1.0},
        )
    }
    base = {
        Role.CIVILIAN: (CivilianStrategy, {"nomination_prob": 0.3}),
        Role.MAFIA: (MafiaStrategy, {"nomination_prob": 0.3}),
        Role.DON: (DonStrategy, {"nomination_prob": 0.3}),
    }
    results = optimise_all(
        params,
        step=0.1,
        games=10,
        rounds=1,
        target=Role.CIVILIAN,
        seed=0,
        base_config=base,
    )
    assert set(results[Role.SHERIFF]) == {"nomination_prob", "reveal_prob"}
    assert all(0 <= r.win_rate <= 1 for r in results[Role.SHERIFF].values())


def test_optimise_from_config(tmp_path):
    """Running optimisation from a config file should produce results."""

    config_text = (
        """
        params:
          CIVILIAN:
            strategy: CivilianStrategy
            params:
              nomination_prob: 0.4
          SHERIFF:
            strategy: SheriffStrategy
            params:
              reveal_prob: 1.0
              nomination_prob: 0.3
        base:
          MAFIA:
            strategy: MafiaStrategy
            params:
              nomination_prob: 0.3
          DON:
            strategy: DonStrategy
            params:
              nomination_prob: 0.3
        games: 20
        rounds: 1
        step: 0.1
        target: CIVILIAN
        seed: 0
        """
    )
    cfg = tmp_path / "opt.yaml"
    cfg.write_text(config_text)
    results = optimise_from_config(cfg)
    civ = results[Role.CIVILIAN]["nomination_prob"]
    assert civ.value < 0.4
    assert 0 <= civ.win_rate <= 1
    assert set(results[Role.SHERIFF]) == {"reveal_prob", "nomination_prob"}


def test_config_single_param_example():
    """The single-parameter example config should optimise one value."""

    cfg = Path(__file__).resolve().parent.parent / "example_configs" / "optimization_civilian.yaml"
    results = optimise_from_config(cfg)
    assert set(results) == {Role.CIVILIAN}
    civ = results[Role.CIVILIAN]["nomination_prob"]
    assert civ.value < 0.4
    assert 0 <= civ.win_rate <= 1


def test_config_single_role_all_params_example():
    """The single-role example should yield results for all its parameters."""

    cfg = Path(__file__).resolve().parent.parent / "example_configs" / "optimization_sheriff.yaml"
    results = optimise_from_config(cfg)
    assert set(results) == {Role.SHERIFF}
    assert set(results[Role.SHERIFF]) == {"nomination_prob", "reveal_prob"}
    assert all(0 <= r.win_rate <= 1 for r in results[Role.SHERIFF].values())

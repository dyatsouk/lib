"""Parameter optimisation helpers for Mafia strategies.

The module implements simple hill-climbing optimisation to improve
strategy parameters based on simulation win rates.  It can optimise a
single role parameter or iterate over multiple roles sequentially.
While more advanced approaches like `Bayesian optimisation`_ exist, a
lightweight hill-climbing search is sufficient for small parameter
spaces and avoids external dependencies.

.. _Bayesian optimisation: https://en.wikipedia.org/wiki/Bayesian_optimization
"""

from __future__ import annotations

import random
from dataclasses import dataclass
from typing import Dict, Mapping, Tuple, Type

from ..roles import Role
from ..strategies import BaseStrategy
from ..simulate import simulate_games


@dataclass
class OptimisationResult:
    """Outcome of an optimisation run."""

    value: float
    win_rate: float


def optimise_parameter(
    role: Role,
    strategy: Type[BaseStrategy],
    param: str,
    start: float,
    *,
    step: float = 0.1,
    games: int = 50,
    iterations: int = 5,
    target: Role | None = None,
    base_config: Mapping[Role, Tuple[Type[BaseStrategy], dict]] | None = None,
    seed: int | None = None,
) -> OptimisationResult:
    """Optimise a single strategy parameter for ``role``.

    The function performs a simple hill-climbing search.  Starting from
    ``start`` it evaluates the win rate with the parameter nudged up and
    down by ``step``.  If either direction improves the rate the parameter
    is updated and the process repeats with a halved step size.

    Parameters
    ----------
    role : Role
        Role whose strategy parameter is optimised.
    strategy : Type[BaseStrategy]
        Strategy class to instantiate for ``role``.
    param : str
        Name of the constructor argument controlling the parameter.
    start : float
        Initial parameter value.
    step : float, optional
        Step size for the hill climb, by default ``0.1``.
    games : int, optional
        Number of games to simulate per evaluation, by default ``50``.
    iterations : int, optional
        Maximum number of optimisation iterations, by default ``5``.
    target : Role, optional
        Role whose win rate is measured.  Defaults to ``role``.
    base_config : mapping, optional
        Additional configuration for other roles kept constant.
    seed : int, optional
        Random seed used for reproducible simulations.

    Returns
    -------
    OptimisationResult
        Final parameter value and corresponding win rate.
    """

    target = target or role
    config: Dict[Role, Tuple[Type[BaseStrategy], dict]] = (
        dict(base_config) if base_config else {}
    )

    def evaluate(value: float) -> float:
        cfg = config.copy()
        cfg[role] = (strategy, {param: value})
        if seed is not None:
            random.seed(seed)
        results = simulate_games(games, config=cfg)
        total = sum(results.values()) or 1
        return results.get(target, 0) / total

    current = start
    best_rate = evaluate(current)

    for _ in range(iterations):
        improved = False
        for direction in (-1, 1):
            trial = current + direction * step
            rate = evaluate(trial)
            if rate > best_rate:
                current, best_rate = trial, rate
                improved = True
        if not improved:
            step /= 2
    return OptimisationResult(current, best_rate)


def optimise_all(
    params: Mapping[Role, Tuple[Type[BaseStrategy], str, float]],
    *,
    step: float = 0.1,
    games: int = 50,
    rounds: int = 3,
    target: Role | None = None,
    seed: int | None = None,
) -> Dict[Role, OptimisationResult]:
    """Optimise parameters for multiple roles sequentially.

    Each round performs a coordinate-descent pass calling
    :func:`optimise_parameter` for every entry in ``params`` and feeding
    the updated configuration into subsequent optimisations.

    Parameters
    ----------
    params : mapping
        Mapping of ``Role`` to ``(strategy class, parameter name, start)``.
    step : float, optional
        Initial step size used for all parameters, by default ``0.1``.
    games : int, optional
        Number of games per evaluation, by default ``50``.
    rounds : int, optional
        Number of coordinate-descent rounds, by default ``3``.
    target : Role, optional
        Role whose win rate is measured. Defaults to ``Role.CIVILIAN``.
    seed : int, optional
        Random seed for reproducibility.

    Returns
    -------
    dict
        Mapping of roles to their optimisation results.
    """

    target = target or Role.CIVILIAN
    config: Dict[Role, Tuple[Type[BaseStrategy], dict]] = {}
    results: Dict[Role, OptimisationResult] = {}

    for _ in range(rounds):
        for role, (strategy, param, value) in params.items():
            res = optimise_parameter(
                role,
                strategy,
                param,
                results.get(role, OptimisationResult(value, 0)).value,
                step=step,
                games=games,
                iterations=1,
                target=target,
                base_config=config,
                seed=seed,
            )
            results[role] = res
            config[role] = (strategy, {param: res.value})
        step /= 2
    return results

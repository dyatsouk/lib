"""Configuration utilities for the Mafia simulation.

This module defines helpers to construct games from a JSON configuration
file. The configuration maps each :class:`~mafia.roles.Role` to a strategy
class name and optional constructor parameters.  It enables running
simulations without modifying code, facilitating experimentation with
different player behaviours.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, Tuple, Type

from .roles import Role
from .strategies import (
    BaseStrategy,
    CivilianStrategy,
    DonStrategy,
    MafiaStrategy,
    SheriffStrategy,
    SingleSheriffCivilianStrategy,
    SingleSheriffDonStrategy,
    SingleSheriffMafiaStrategy,
    SingleSheriffSheriffStrategy,
)

# Mapping from strategy name used in the configuration file to the actual
# class object.  Users can extend this mapping when providing custom
# strategies.
STRATEGIES: Dict[str, Type[BaseStrategy]] = {
    "CivilianStrategy": CivilianStrategy,
    "SheriffStrategy": SheriffStrategy,
    "MafiaStrategy": MafiaStrategy,
    "DonStrategy": DonStrategy,
    "SingleSheriffCivilianStrategy": SingleSheriffCivilianStrategy,
    "SingleSheriffSheriffStrategy": SingleSheriffSheriffStrategy,
    "SingleSheriffMafiaStrategy": SingleSheriffMafiaStrategy,
    "SingleSheriffDonStrategy": SingleSheriffDonStrategy,
}


def load_config(path: str | Path) -> Dict[Role, Tuple[Type[BaseStrategy], dict]]:
    """Load a simulation configuration from a JSON file.

    Parameters
    ----------
    path : str or Path
        Path to a JSON file describing strategies per role.

    Returns
    -------
    dict
        Mapping of :class:`Role` to ``(strategy_class, params)`` tuples.
    """

    with open(path, "r", encoding="utf-8") as fh:
        raw = json.load(fh)

    config: Dict[Role, Tuple[Type[BaseStrategy], dict]] = {}
    for role_name, spec in raw.items():
        role = Role[role_name]
        strategy_name = spec["strategy"]
        params = spec.get("params", {})
        strat_cls = STRATEGIES[strategy_name]
        config[role] = (strat_cls, params)
    return config

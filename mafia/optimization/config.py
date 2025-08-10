"""Load optimisation settings from a configuration file.

This module mirrors :mod:`mafia.config` but describes the parameters to
optimise rather than the full simulation setup.  The configuration file is
expected to be JSON or YAML with two sections:

``params``
    Mapping of role names to optimisation directives.  Each entry specifies
    a ``strategy`` class name and either a single parameter via ``param`` /
    ``start`` or a ``params`` mapping of multiple parameters with their
    starting values.  All listed parameters are tuned sequentially.
``base``
    Optional mapping of additional roles that should remain fixed during
    optimisation.  These entries follow the structure used by
    :func:`mafia.config.load_config`.

Additional top level keys configure the optimisation run itself:
``step``, ``games``, ``rounds``, ``target`` and ``seed``.  See
:func:`mafia.optimization.optimise_all` for their meaning.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, Tuple, Type

from ..roles import Role
from ..strategies import BaseStrategy
from ..config import _get_strategy_class


# Type aliases for readability
# Each role maps to a strategy class and a dictionary of parameter start values
ParamSpec = Tuple[Type[BaseStrategy], Dict[str, float]]
ConfigMap = Dict[Role, Tuple[Type[BaseStrategy], dict]]


def _load_raw(path: Path) -> dict:
    """Return the raw JSON/YAML document as a dictionary."""

    with open(path, "r", encoding="utf-8") as fh:
        if path.suffix.lower() in {".yaml", ".yml"}:
            # Import lazily to avoid mandatory PyYAML dependency
            import yaml  # type: ignore

            return yaml.safe_load(fh) or {}
        return json.load(fh)


def load_optimisation_config(path: str | Path) -> Tuple[Dict[Role, ParamSpec], ConfigMap, dict]:
    """Parse an optimisation configuration file.

    Parameters
    ----------
    path:
        Location of the JSON/YAML document describing the optimisation
        parameters.

    Returns
    -------
    tuple
        ``(params, base_config, options)`` where ``params`` maps roles to a
        strategy class and dictionary of parameter start values suitable for
        :func:`mafia.optimization.optimise_all`, ``base_config`` holds fixed
        role strategies and ``options`` contains additional keyword
        arguments for the optimiser.
    """

    path = Path(path)
    raw = _load_raw(path)

    params: Dict[Role, ParamSpec] = {}
    for role_name, spec in (raw.get("params") or {}).items():
        role = Role[role_name]
        strat = _get_strategy_class(spec["strategy"])
        if "params" in spec:
            # Multiple parameters specified explicitly
            param_map = {k: float(v) for k, v in spec["params"].items()}
        else:
            # Legacy single-parameter format
            param_map = {spec["param"]: float(spec["start"])}
        params[role] = (strat, param_map)

    base_config: ConfigMap = {}
    for role_name, spec in (raw.get("base") or {}).items():
        role = Role[role_name]
        strat = _get_strategy_class(spec["strategy"])
        opts = spec.get("params", {})
        base_config[role] = (strat, opts)

    target_name = raw.get("target")
    options = {
        "step": raw.get("step", 0.1),
        "games": raw.get("games", 50),
        "rounds": raw.get("rounds", 3),
        "target": Role[target_name] if target_name else Role.CIVILIAN,
        "seed": raw.get("seed"),
    }
    return params, base_config, options

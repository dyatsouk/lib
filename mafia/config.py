"""Configuration utilities for the Mafia simulation.

The module provides helpers to construct games from an external
configuration file.  Originally configurations were expected to be JSON
documents, but the loader now also understands YAML for increased
flexibility.  Each entry maps a :class:`~mafia.roles.Role` to a strategy class
name and optional constructor parameters.  Strategy classes are resolved by
name at runtime which removes the need to keep a manual mapping up to date
whenever new strategies are added.
"""

from __future__ import annotations

import json
import inspect
from pathlib import Path
from typing import Dict, Tuple, Type

from .roles import Role
from . import strategies as _strategies
from .strategies import BaseStrategy


def _get_strategy_class(name: str) -> Type[BaseStrategy]:
    """Return a strategy class by name.

    The lookup searches attributes of :mod:`mafia.strategies` for a class with
    the requested ``name``.  A ``KeyError`` is raised when no such class exists
    or the attribute found is not a subclass of :class:`BaseStrategy`.
    This introspection based approach means newly added strategies are
    automatically available to configuration files without updating a manual
    registry.
    """

    try:
        obj = getattr(_strategies, name)
    except AttributeError as exc:  # pragma: no cover - defensive programming
        raise KeyError(f"Unknown strategy '{name}'") from exc

    if inspect.isclass(obj) and issubclass(obj, BaseStrategy):
        return obj
    raise KeyError(f"'{name}' is not a valid strategy class")

def load_config(path: str | Path) -> Dict[Role, Tuple[Type[BaseStrategy], dict]]:
    """Load a simulation configuration from a JSON or YAML file.

    The loader inspects the file extension to decide whether to parse JSON
    (``.json``) or YAML (``.yaml``/``.yml``).  Each role specified in the file is
    mapped to a strategy class name and optional constructor parameters.

    Parameters
    ----------
    path : str or Path
        Path to a configuration file.

    Returns
    -------
    dict
        Mapping of :class:`Role` to ``(strategy_class, params)`` tuples.
    """

    path = Path(path)
    with open(path, "r", encoding="utf-8") as fh:
        if path.suffix.lower() in {".yaml", ".yml"}:
            # Import lazily so that JSON users do not need PyYAML installed
            try:  # pragma: no cover - import error handled for completeness
                import yaml  # type: ignore
            except ImportError as exc:  # pragma: no cover
                raise ImportError(
                    "PyYAML is required to load YAML configuration files"
                ) from exc
            raw = yaml.safe_load(fh) or {}
        else:
            raw = json.load(fh)

    config: Dict[Role, Tuple[Type[BaseStrategy], dict]] = {}
    for role_name, spec in raw.items():
        role = Role[role_name]
        strategy_name = spec["strategy"]
        params = spec.get("params", {})
        strat_cls = _get_strategy_class(strategy_name)
        config[role] = (strat_cls, params)
    return config

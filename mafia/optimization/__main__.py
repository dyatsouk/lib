"""CLI entry point for optimisation routines.

Running ``python -m mafia.optimization config.yaml`` executes the hill-climbing
search described in the configuration file and prints the resulting parameter
values and win rates.
"""

from __future__ import annotations

import argparse

from . import optimise_from_config


def main() -> None:
    """Parse command line arguments and run the optimiser."""

    parser = argparse.ArgumentParser(
        description="Optimise strategy parameters via simulations",
    )
    parser.add_argument(
        "config",
        type=str,
        help="Path to JSON or YAML optimisation configuration",
    )
    args = parser.parse_args()

    results = optimise_from_config(args.config)
    for role, params in results.items():
        for param, res in params.items():
            print(f"{role.name}.{param}: {res.value:.3f} -> {res.win_rate:.1%}")


if __name__ == "__main__":
    main()

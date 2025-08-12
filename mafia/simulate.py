import random
from collections import Counter
from pathlib import Path
from typing import Dict, Mapping, Tuple, Type

from tqdm.auto import tqdm

from .roles import Role
from .player import Player
from .strategies import (
    BaseStrategy,
    CivilianStrategy,
    DonStrategy,
    MafiaStrategy,
    SheriffStrategy,
)
from .game import Game
from .logger import GameLogger
from .events import EventDispatcher
from .history import GameHistoryDB
from .config import load_config


def create_game(
    logger: GameLogger | None = None,
    config: Mapping[Role, Tuple[Type[BaseStrategy], dict]] | None = None,
) -> Game:
    """Create a new game instance.

    Parameters
    ----------
    logger : GameLogger, optional
        Optional logger used to record game events.
    config : mapping, optional
        Mapping from :class:`Role` to ``(strategy_class, params)`` tuples as
        produced by :func:`mafia.config.load_config` from JSON or YAML. When
        omitted, default strategies are used.
    """

    roles = [Role.SHERIFF] + [Role.CIVILIAN] * 6 + [Role.DON] + [Role.MAFIA] * 2
    random.shuffle(roles)
    players = []
    for pid, role in enumerate(roles):
        if config and role in config:
            strat_cls, params = config[role]
            strat = strat_cls(**params)
        elif role == Role.CIVILIAN:
            strat = CivilianStrategy()
        elif role == Role.SHERIFF:
            strat = SheriffStrategy()
        elif role == Role.DON:
            strat = DonStrategy()
        else:
            strat = MafiaStrategy()
        players.append(Player(pid=pid, role=role, strategy=strat))
    dispatcher = EventDispatcher()
    if logger:
        logger.attach(dispatcher)
    return Game(players, dispatcher=dispatcher)


def simulate_games(
    n: int,
    logger: GameLogger | None = None,
    db: GameHistoryDB | None = None,
    config: Mapping[Role, Tuple[Type[BaseStrategy], dict]] | str | Path | None = None,
) -> Dict[Role, int]:
    """Run ``n`` games and tally the winners.

    A progress bar is displayed via :mod:`tqdm` so that long simulations
    provide feedback to the user.

    Parameters
    ----------
    n : int
        Number of games to simulate.
    logger : GameLogger, optional
        Logger used for recording events.
    db : GameHistoryDB, optional
        Optional database for storing summaries.
    config : mapping or str or Path, optional
        Either a configuration mapping or a path to a JSON or YAML
        configuration file. When ``None`` the default strategies are used.
    """

    if isinstance(config, (str, Path)):
        config = load_config(config)

    results = Counter()
    # Iterate over the requested number of games while updating a progress bar
    # so users can track long-running simulations.
    for i in tqdm(range(n), desc="Simulating games"):
        if logger:
            logger.log(f"game {i + 1}")
        game = create_game(logger, config)
        winner = game.run()
        results[winner] += 1
        if db:
            db.log_game(game, winner)
    return results


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Simulate sports mafia games")
    parser.add_argument("n", type=int, nargs="?", default=10, help="Number of games to simulate")
    parser.add_argument("-v", "--verbose", action="store_true", help="Log actions to stdout")
    parser.add_argument("-l", "--log", action="store_true", help="Write action log to simul.log")
    parser.add_argument(
        "--db",
        nargs="?",
        const="games.db",
        default=None,
        help="Path to SQLite database for storing game summaries (defaults to games.db)",
    )
    parser.add_argument(
        "--config",
        type=str,
        default=None,
        help="Path to JSON or YAML file describing strategies for each role",
    )
    args = parser.parse_args()

    logger = None
    if args.verbose or args.log:
        logger = GameLogger(verbose=args.verbose, log_to_file=args.log)
    db = GameHistoryDB(args.db) if args.db is not None else None
    results = simulate_games(args.n, logger, db, config=args.config)
    if logger:
        logger.close()
    if db:
        db.close()
    total = sum(results.values())
    for role, count in results.items():
        print(f"{role.name} wins: {count} ({count/total:.1%})")

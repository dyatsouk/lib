import random
from collections import Counter
from typing import Dict

from .roles import Role
from .player import Player
from .strategies import CivilianStrategy, SheriffStrategy, MafiaStrategy, DonStrategy
from .game import Game
from .logger import GameLogger
from .history import GameHistoryDB


def create_game(logger: GameLogger | None = None) -> Game:
    roles = [Role.SHERIFF] + [Role.CIVILIAN] * 6 + [Role.DON] + [Role.MAFIA] * 2
    random.shuffle(roles)
    players = []
    for pid, role in enumerate(roles):
        if role == Role.CIVILIAN:
            strat = CivilianStrategy()
        elif role == Role.SHERIFF:
            strat = SheriffStrategy()
        elif role == Role.DON:
            strat = DonStrategy()
        else:
            strat = MafiaStrategy()
        players.append(Player(pid=pid, role=role, strategy=strat))
    return Game(players, logger=logger)


def simulate_games(
    n: int,
    logger: GameLogger | None = None,
    db: GameHistoryDB | None = None,
) -> Dict[Role, int]:
    results = Counter()
    for i in range(n):
        if logger:
            logger.log(f"game {i + 1}")
        game = create_game(logger)
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
    parser.add_argument("--db", type=str, help="Path to SQLite database for storing game summaries")
    args = parser.parse_args()

    logger = None
    if args.verbose or args.log:
        logger = GameLogger(verbose=args.verbose, log_to_file=args.log)
    db = GameHistoryDB(args.db) if args.db else None
    results = simulate_games(args.n, logger, db)
    if logger:
        logger.close()
    if db:
        db.close()
    total = sum(results.values())
    for role, count in results.items():
        print(f"{role.name} wins: {count} ({count/total:.1%})")

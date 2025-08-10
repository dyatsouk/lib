import random
from collections import Counter
from typing import Dict

from .roles import Role
from .player import Player
from .strategies import CivilianStrategy, SheriffStrategy, MafiaStrategy, DonStrategy
from .game import Game


def create_game() -> Game:
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
    return Game(players)


def simulate_games(n: int) -> Dict[Role, int]:
    results = Counter()
    for _ in range(n):
        game = create_game()
        winner = game.run()
        results[winner] += 1
    return results


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Simulate sports mafia games")
    parser.add_argument("n", type=int, nargs="?", default=10, help="Number of games to simulate")
    args = parser.parse_args()

    results = simulate_games(args.n)
    total = sum(results.values())
    for role, count in results.items():
        print(f"{role.name} wins: {count} ({count/total:.1%})")

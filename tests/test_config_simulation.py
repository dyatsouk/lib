import json
import random
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))

from mafia.config import load_config
from mafia.roles import Role
from mafia.simulate import create_game, simulate_games
from mafia.strategies import (
    CivilianStrategy,
    DonStrategy,
    MafiaStrategy,
    SheriffStrategy,
    SingleSheriffCivilianStrategy,
    SingleSheriffSheriffStrategy,
)


def test_create_game_from_config(tmp_path):
    cfg = {
        "CIVILIAN": {"strategy": "CivilianStrategy", "params": {"nomination_prob": 0.1}},
        "SHERIFF": {
            "strategy": "SheriffStrategy",
            "params": {"nomination_prob": 0.2, "reveal_prob": 0.9},
        },
        "MAFIA": {"strategy": "MafiaStrategy", "params": {"nomination_prob": 0.4}},
        "DON": {"strategy": "DonStrategy", "params": {"nomination_prob": 0.5}},
    }
    path = tmp_path / "cfg.json"
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(cfg, fh)

    config = load_config(path)
    random.seed(0)
    game = create_game(config=config)

    for p in game.players:
        if p.role == Role.CIVILIAN:
            assert isinstance(p.strategy, CivilianStrategy)
            assert p.strategy.nomination_prob == 0.1
        elif p.role == Role.SHERIFF:
            assert isinstance(p.strategy, SheriffStrategy)
            assert p.strategy.nomination_prob == 0.2
            assert p.strategy.reveal_prob == 0.9
        elif p.role == Role.MAFIA:
            assert isinstance(p.strategy, MafiaStrategy)
            assert p.strategy.nomination_prob == 0.4
        elif p.role == Role.DON:
            assert isinstance(p.strategy, DonStrategy)
            assert p.strategy.nomination_prob == 0.5


def test_single_sheriff_aliases(tmp_path):
    cfg = {
        "CIVILIAN": {
            "strategy": "SingleSheriffCivilianStrategy",
            "params": {"nomination_prob": 0.4},
        },
        "SHERIFF": {
            "strategy": "SingleSheriffSheriffStrategy",
            "params": {"reveal_prob": 0.1},
        },
        "MAFIA": {"strategy": "SingleSheriffMafiaStrategy"},
        "DON": {"strategy": "SingleSheriffDonStrategy"},
    }
    path = tmp_path / "single.json"
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(cfg, fh)

    config = load_config(path)
    random.seed(1)
    game = create_game(config=config)

    civilian = next(p for p in game.players if p.role == Role.CIVILIAN)
    sheriff = next(p for p in game.players if p.role == Role.SHERIFF)

    assert isinstance(civilian.strategy, SingleSheriffCivilianStrategy)
    assert civilian.strategy.random_nomination_chance == 0.4
    assert isinstance(sheriff.strategy, SingleSheriffSheriffStrategy)
    assert sheriff.strategy.reveal_probability == 0.1


def test_simulate_games_with_config(tmp_path):
    cfg = {
        "CIVILIAN": {"strategy": "CivilianStrategy"},
        "SHERIFF": {"strategy": "SheriffStrategy"},
        "MAFIA": {"strategy": "MafiaStrategy"},
        "DON": {"strategy": "DonStrategy"},
    }
    path = tmp_path / "basic.json"
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(cfg, fh)

    results = simulate_games(2, config=path)
    assert sum(results.values()) == 2

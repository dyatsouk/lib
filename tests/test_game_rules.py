from mafia.game import Game
from mafia.player import Player
from mafia.roles import Role
from mafia.actions import SpeechAction, RoundLog
from mafia.strategies import BaseStrategy, SheriffStrategy


class NominateAbstainStrategy(BaseStrategy):
    """Strategy that nominates player 1 but attempts to abstain from voting."""

    def speak(self, player, game):
        return SpeechAction(nomination=1)

    def vote(self, player, game, nominations):
        return None


class AbstainStrategy(BaseStrategy):
    """Strategy that always abstains from voting."""

    def vote(self, player, game, nominations):
        return None


class ListLogger:
    """Simple logger collecting messages for assertions."""

    def __init__(self):
        self.messages = []

    def log(self, message):  # pragma: no cover - trivial
        self.messages.append(message)


class KillSheriffStrategy(BaseStrategy):
    """Mafia strategy that always kills the sheriff at night."""

    def speak(self, player, game):
        return SpeechAction()

    def vote(self, player, game, nominations):
        return None

    def mafia_kill(self, player, game, candidates):
        return 0


# Test 1: voting enforcement

def test_players_cannot_abstain_when_candidates_exist():
    players = [
        Player(0, Role.CIVILIAN, NominateAbstainStrategy()),
        Player(1, Role.CIVILIAN, AbstainStrategy()),
    ]
    game = Game(players)
    day = game.day_phase(1)
    assert all(v.target == 1 for v in day.votes)


# Test 2: logging when night victim has no claims

def test_night_victim_without_claims_logged():
    logger = ListLogger()
    players = [
        Player(0, Role.CIVILIAN, BaseStrategy()),
        Player(1, Role.DON, KillSheriffStrategy()),
        Player(2, Role.CIVILIAN, BaseStrategy()),
    ]
    game = Game(players, logger=logger)
    day1 = game.day_phase(1)
    night1 = game.night_phase(1)
    game.history.append(RoundLog(day=day1, night=night1))
    game.day_phase(2)
    assert any("player 1 has no claims" in m for m in logger.messages)


# Test 3: sheriff gets final check when killed

def test_sheriff_killed_still_checks():
    players = [
        Player(0, Role.SHERIFF, SheriffStrategy()),
        Player(1, Role.MAFIA, KillSheriffStrategy()),
    ]
    game = Game(players)
    night = game.night_phase(1)
    assert night.kill == 0
    assert night.sheriff_check is not None
    assert night.sheriff_check.target == 1
    assert not players[0].alive

from mafia.game import Game
from mafia.player import Player
from mafia.roles import Role
from mafia.actions import SpeechAction
from mafia.strategies import BaseStrategy


class SimpleSheriffStrategy(BaseStrategy):
    """Sheriff strategy that deterministically checks player 1."""

    def speak(self, player, game):
        return SpeechAction()

    def vote(self, player, game, nominations):
        return None

    def sheriff_check(self, player, game, candidates):
        return 1 if candidates else None

    def remember(self, target, result):
        """Record check results; no-op for tests."""
        pass


class KillSheriffStrategy(BaseStrategy):
    """Mafia/Don strategy that always targets the sheriff."""

    def __init__(self):
        self.checked = set()
        self.known_sheriff = None

    def speak(self, player, game):
        return SpeechAction()

    def vote(self, player, game, nominations):
        return None

    def mafia_kill(self, player, game, candidates):
        return 0

    def don_check(self, player, game, candidates):
        return 3 if candidates else None


class PassiveStrategy(BaseStrategy):
    """Strategy performing no special actions."""

    pass


def test_game_delegates_night_actions(monkeypatch):
    """Night actions are supplied by role hooks rather than Game role checks."""

    players = [
        Player(0, Role.SHERIFF, SimpleSheriffStrategy()),
        Player(1, Role.MAFIA, KillSheriffStrategy()),
        Player(2, Role.DON, KillSheriffStrategy()),
        Player(3, Role.CIVILIAN, PassiveStrategy()),
    ]
    game = Game(players)

    called: list[int] = []
    original = Role.perform_night_action

    def tracking(self, player, game):
        called.append(player.pid)
        return original(self, player, game)

    monkeypatch.setattr(Role, "perform_night_action", tracking)
    night = game.night_phase(1)

    # All players should have been asked to act
    assert set(called) == {0, 1, 2, 3}
    assert night.kill == 0
    assert night.sheriff_check and night.sheriff_check.target == 1
    assert night.don_check and night.don_check.target == 3
    assert not players[0].alive

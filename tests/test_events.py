"""Tests for the event dispatcher and logging behaviour."""

from mafia.actions import SpeechAction, SpeechLog
from mafia.events import EventDispatcher
from mafia.game import Game
from mafia.logger import GameLogger
from mafia.player import Player
from mafia.roles import Role
from mafia.strategies import BaseStrategy


class SilentStrategy(BaseStrategy):
    """Strategy performing no nominations or votes."""

    def speak(self, player, game):
        return SpeechAction()

    def vote(self, player, game, nominations):
        return None


class NominateStrategy(BaseStrategy):
    """Strategy nominating a predefined player and voting for them."""

    def __init__(self, nomination, vote_target):
        self.nomination = nomination
        self.vote_target = vote_target

    def speak(self, player, game):
        return SpeechAction(nomination=self.nomination)

    def vote(self, player, game, nominations):
        return self.vote_target


class KillFirstStrategy(BaseStrategy):
    """Mafia strategy that always kills the first candidate."""

    def mafia_kill(self, player, game, candidates):  # pragma: no cover - deterministic
        for cand in candidates:
            if cand != player.pid:
                return cand
        return None


def test_speech_event_emitted():
    """Adding a speech results in a ``speech_added`` event."""

    dispatcher = EventDispatcher()
    events = []
    dispatcher.subscribe("speech_added", lambda **p: events.append(p))
    players = [Player(0, Role.CIVILIAN, SilentStrategy())]
    game = Game(players, dispatcher=dispatcher)
    game.add_speech(SpeechLog(speaker=0, action=SpeechAction()), day_no=1)
    assert events and events[0]["speech"].speaker == 0


def test_vote_event_emitted():
    """Casting votes fires ``vote_cast`` events."""

    dispatcher = EventDispatcher()
    events = []
    dispatcher.subscribe("vote_cast", lambda **p: events.append(p))
    players = [
        Player(0, Role.CIVILIAN, NominateStrategy(1, 1)),
        Player(1, Role.CIVILIAN, NominateStrategy(0, 0)),
    ]
    game = Game(players, dispatcher=dispatcher)
    game.day_phase(1)
    assert any(e["voter"] == 1 and e["target"] == 0 for e in events)


def test_night_action_event_emitted():
    """Night actions trigger ``night_action`` events."""

    dispatcher = EventDispatcher()
    events = []
    dispatcher.subscribe("night_action", lambda **p: events.append(p))
    players = [
        Player(0, Role.MAFIA, KillFirstStrategy()),
        Player(1, Role.CIVILIAN, SilentStrategy()),
    ]
    game = Game(players, dispatcher=dispatcher)
    game.night_phase(1)
    assert any(e["action"] == "mafia_kill" for e in events)


def test_logging_can_be_suppressed(capsys):
    """No output is produced when no logger is attached."""

    dispatcher = EventDispatcher()
    players = [Player(0, Role.CIVILIAN, SilentStrategy())]
    game = Game(players, dispatcher=dispatcher)
    game.add_speech(SpeechLog(speaker=0, action=SpeechAction()), day_no=1)
    captured = capsys.readouterr()
    assert captured.out == ""


def test_custom_logger_can_replace():
    """A custom logger can subscribe to events and collect messages."""

    dispatcher = EventDispatcher()

    class CollectingLogger(GameLogger):  # pragma: no cover - simple storage
        def __init__(self):
            super().__init__(verbose=False)
            self.messages = []

        def log(self, message: str) -> None:  # type: ignore[override]
            self.messages.append(message)

    logger = CollectingLogger()
    logger.attach(dispatcher)
    players = [Player(0, Role.CIVILIAN, SilentStrategy())]
    game = Game(players, dispatcher=dispatcher)
    game.day_phase(1)
    assert any("day" in m for m in logger.messages)

import random
from mafia.game import Game
from mafia.player import Player
from mafia.roles import Role
from mafia.actions import SpeechAction, SheriffClaim, SpeechLog, RoundLog
from mafia.strategies import (
    BaseStrategy,
    SingleSheriffCivilianStrategy,
    SingleSheriffSheriffStrategy,
    SingleSheriffMafiaStrategy,
    SingleSheriffDonStrategy,
)


class AlwaysKillStrategy(SingleSheriffMafiaStrategy):
    """Test mafia strategy that always kills a predefined target.

    Attributes
    ----------
    target : int
        Player id that will always be chosen for the night kill.
    """

    def __init__(self, target):
        super().__init__()
        self.target = target

    def mafia_kill(self, player, game, candidates):
        return self.target


class NominateVoteStrategy(BaseStrategy):
    """Always nominates and votes for player ``0``."""

    def speak(self, player, game):
        return SpeechAction(nomination=0)

    def vote(self, player, game, nominations):
        return 0


class VoteStrategy(BaseStrategy):
    """Test strategy that always votes for player ``0``."""

    def vote(self, player, game, nominations):
        return 0


def test_night_victim_speaks_next_day():
    # Player 1 (mafia) kills player 0 during the first night. On day 2 the
    # victim should get a speech with no nomination option.
    players = [
        Player(0, Role.CIVILIAN, BaseStrategy()),
        Player(1, Role.DON, AlwaysKillStrategy(target=0)),
        Player(2, Role.CIVILIAN, BaseStrategy()),
    ]
    game = Game(players)
    day1 = game.day_phase(1)
    night1 = game.night_phase(1)
    game.history.append(RoundLog(day=day1, night=night1))
    day2 = game.day_phase(2)
    assert day2.speeches[0].speaker == 0  # night victim speaks
    assert day2.speeches[0].action.nomination is None  # cannot nominate


def test_eliminated_player_speaks_after_vote():
    """Eliminated player receives final speech after a vote."""

    players = [
        Player(0, Role.CIVILIAN, BaseStrategy()),
        Player(1, Role.CIVILIAN, NominateVoteStrategy()),
        Player(2, Role.CIVILIAN, VoteStrategy()),
    ]
    game = Game(players)
    # Use day number 2 to bypass the first-day single-nomination exemption.
    day = game.day_phase(2)
    assert day.eliminated == [0]
    assert day.speeches[-1].speaker == 0  # eliminated player speaks last
    assert day.speeches[-1].action.nomination is None  # no nomination allowed


def test_single_sheriff_civilian_strategy():
    # Civilian should trust the sheriff's claim: vote and nominate the
    # sheriff-checked mafia while avoiding checked civilians.
    players = [
        Player(0, Role.SHERIFF, BaseStrategy()),
        Player(1, Role.MAFIA, BaseStrategy()),
        Player(2, Role.CIVILIAN, SingleSheriffCivilianStrategy()),
    ]
    game = Game(players)
    game.current_speeches = [
        SpeechLog(
            speaker=0,
            action=SpeechAction(
                nomination=1,
                claims=[SheriffClaim(0, 1, True), SheriffClaim(0, 2, False)],
            ),
        )
    ]
    vote = players[2].vote(game, [1, 2])
    assert vote == 1  # follows sheriff's vote
    speech = players[2].speak(game)
    assert speech.nomination == 1  # nominates checked mafia


def test_civilians_follow_revealed_sheriff():
    """All civilians should mirror a revealed sheriff's nomination and vote."""

    players = [
        Player(0, Role.SHERIFF, BaseStrategy()),
        Player(1, Role.MAFIA, BaseStrategy()),
        Player(2, Role.CIVILIAN, SingleSheriffCivilianStrategy()),
        Player(3, Role.CIVILIAN, SingleSheriffCivilianStrategy()),
    ]
    game = Game(players)
    game.current_speeches = [
        SpeechLog(
            speaker=0,
            action=SpeechAction(
                nomination=1,
                claims=[SheriffClaim(0, 1, True)],
            ),
        )
    ]

    for pid in (2, 3):
        speech = players[pid].speak(game)
        assert speech.nomination == 1
        vote = players[pid].vote(game, [1, 2, 3])
        assert vote == 1


def test_civilian_targeted_by_sheriff_nominate_elsewhere():
    """A civilian accused by the sheriff should choose a different target."""

    players = [
        Player(0, Role.SHERIFF, BaseStrategy()),
        Player(1, Role.MAFIA, BaseStrategy()),
        Player(2, Role.CIVILIAN, SingleSheriffCivilianStrategy()),
        Player(3, Role.CIVILIAN, SingleSheriffCivilianStrategy()),
    ]
    game = Game(players)
    game.current_speeches = [
        SpeechLog(
            speaker=0,
            action=SpeechAction(
                nomination=2,
                claims=[
                    SheriffClaim(0, 2, True),
                    SheriffClaim(0, 3, False),
                ],
            ),
        )
    ]

    # Ensure nomination occurs by forcing random.random() to return 0.0
    original_random = random.random
    random.random = lambda: 0.0
    try:
        speech = players[2].speak(game)
    finally:
        random.random = original_random

    assert speech.nomination == 1  # avoids self, sheriff and cleared civilian
    vote = players[2].vote(game, [1, 2, 3])
    assert vote == 1  # votes for alternative suspect


def test_random_nomination_probability_configurable():
    """Customising random nomination chance should influence behaviour."""

    players = [
        Player(
            0,
            Role.CIVILIAN,
            SingleSheriffCivilianStrategy(random_nomination_chance=0.0),
        ),
        Player(1, Role.MAFIA, BaseStrategy()),
    ]
    game = Game(players)

    # Force RNG low to prove that with probability 0 no nomination occurs.
    original_random = random.random
    random.random = lambda: 0.0
    try:
        speech = players[0].speak(game)
    finally:
        random.random = original_random

    assert speech.nomination is None


def test_single_sheriff_sheriff_reveals_after_death():
    # Even if the sheriff stayed hidden during the game, his last words should
    # reveal all check results.
    random.seed(0)
    strategy = SingleSheriffSheriffStrategy(reveal_probability=0.0)
    player = Player(0, Role.SHERIFF, strategy)
    strategy.remember(1, True)
    strategy.remember(2, False)
    game = Game([player])
    action = player.last_words(game)
    claims = {(c.target, c.is_mafia) for c in action.claims}
    assert claims == {(1, True), (2, False)}


def test_single_sheriff_sheriff_reveal_each_round():
    """Sheriff should reconsider revealing every time he speaks."""

    strategy = SingleSheriffSheriffStrategy(reveal_probability=0.5)
    player = Player(0, Role.SHERIFF, strategy)
    strategy.remember(1, True)
    game = Game([player])

    # first call: random value > 0.5 -> stays hidden
    seq = iter([0.6, 0.4])

    def fake_random():
        return next(seq)

    original_random = random.random
    random.random = fake_random
    try:
        speech1 = player.speak(game)
        assert not speech1.claims  # hidden, no claims
        speech2 = player.speak(game)
        assert [(c.target, c.is_mafia) for c in speech2.claims] == [(1, True)]  # reveals on second call
    finally:
        random.random = original_random


def test_single_sheriff_mafia_kill_priorities():
    # Mafia should prioritise killing the real sheriff, then a claimant, then
    # any civilians confirmed by the sheriff.
    players = [
        Player(0, Role.SHERIFF, BaseStrategy()),
        Player(1, Role.MAFIA, SingleSheriffMafiaStrategy()),
        Player(2, Role.CIVILIAN, BaseStrategy()),
        Player(3, Role.CIVILIAN, BaseStrategy()),
    ]
    game = Game(players)
    mafia = players[1]
    # known sheriff
    mafia.strategy.known_sheriff = 0
    target = mafia.mafia_kill(game, [0, 2, 3])
    assert target == 0
    # claimed sheriff
    mafia.strategy.known_sheriff = None
    game.current_speeches = [
        SpeechLog(
            speaker=0,
            action=SpeechAction(claims=[SheriffClaim(0, 2, False)]),
        )
    ]
    target = mafia.mafia_kill(game, [0, 2, 3])
    assert target == 0
    # kill checked civilian
    mafia.strategy.claimed_sheriff = None
    mafia.strategy.kill_queue = []
    mafia.strategy._processed_speeches = set()
    mafia.strategy._next_history_index = 0
    mafia.strategy._update_claims(game)
    mafia.strategy.claimed_sheriff = None
    game.current_speeches = []
    target = mafia.mafia_kill(game, [0, 2, 3])
    assert target == 2


def test_single_sheriff_don_check():
    # Don should avoid checking the same player twice.
    random.seed(0)
    strategy = SingleSheriffDonStrategy()
    player = Player(0, Role.DON, strategy)
    others = [
        Player(1, Role.CIVILIAN, BaseStrategy()),
        Player(2, Role.SHERIFF, BaseStrategy()),
    ]
    game = Game([player] + others)
    candidates = [1, 2]
    first = player.don_check(game, candidates)
    strategy.checked.add(first)
    second = player.don_check(game, candidates)
    assert first in candidates and second in candidates and first != second

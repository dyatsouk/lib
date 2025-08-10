from mafia.game import Game
from mafia.player import Player
from mafia.roles import Role
from mafia.actions import SpeechAction, RoundLog
from mafia.strategies import BaseStrategy, SheriffStrategy


class NominateAbstainStrategy(BaseStrategy):
    """Strategy that nominates a chosen player but abstains from voting.

    Parameters
    ----------
    nomination_target : int, optional
        Player id to nominate during ``speak``, by default ``1``.
    """

    def __init__(self, nomination_target=1):
        self.nomination_target = nomination_target

    def speak(self, player, game):
        return SpeechAction(nomination=self.nomination_target)

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


class FixedVotingStrategy(BaseStrategy):
    """Deterministic strategy used for tie-vote resolution tests."""

    def __init__(self, nomination, first_vote, second_vote, eliminate):
        self.nomination = nomination
        self.first_vote = first_vote
        self.second_vote = second_vote
        self.eliminate = eliminate
        self._vote_count = 0

    def speak(self, player, game):
        return SpeechAction(nomination=self.nomination)

    def vote(self, player, game, nominations):
        self._vote_count += 1
        return self.first_vote if self._vote_count == 1 else self.second_vote

    def vote_elimination(self, player, game, candidates):
        return self.eliminate


class MultiRoundStrategy(BaseStrategy):
    """Strategy returning a predefined sequence of vote targets.

    Parameters
    ----------
    nomination : Optional[int]
        Initial nomination during ``speak``.
    votes : list[int]
        Ordered list of vote targets for successive voting rounds. If
        more votes are required than provided, the last target is
        repeated.
    eliminate : bool
        Whether this player votes to eliminate all tied candidates in
        the final mass-elimination vote.
    """

    def __init__(self, nomination, votes, eliminate):
        self.nomination = nomination
        self.votes = votes
        self.eliminate = eliminate
        self._idx = 0

    def speak(self, player, game):
        return SpeechAction(nomination=self.nomination)

    def vote(self, player, game, nominations):
        choice = self.votes[self._idx] if self._idx < len(self.votes) else self.votes[-1]
        self._idx += 1
        return choice

    def vote_elimination(self, player, game, candidates):
        return self.eliminate


# Test 1: voting enforcement

def test_players_cannot_abstain_when_candidates_exist():
    """Abstaining when candidates exist defaults the vote to a nominee."""

    players = [
        Player(0, Role.CIVILIAN, NominateAbstainStrategy()),
        Player(1, Role.CIVILIAN, AbstainStrategy()),
    ]
    game = Game(players)
    day = game.day_phase(1)
    assert all(v.target == 1 for v in day.votes)


def test_abstaining_vote_defaults_to_last_nominee():
    """When multiple candidates exist, abstainers vote for the last nomination."""

    players = [
        Player(0, Role.CIVILIAN, NominateAbstainStrategy(1)),
        Player(1, Role.CIVILIAN, NominateAbstainStrategy(2)),
        Player(2, Role.CIVILIAN, AbstainStrategy()),
    ]
    game = Game(players)
    day = game.day_phase(1)
    assert all(v.target == 2 for v in day.votes)
    assert day.eliminated == [2]


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


def test_tied_candidates_eliminated_after_majority():
    """Tied players are eliminated if majority votes for mass elimination."""

    players = [
        Player(0, Role.CIVILIAN, FixedVotingStrategy(1, 1, 1, True)),
        Player(1, Role.CIVILIAN, FixedVotingStrategy(2, 2, 2, False)),
        Player(2, Role.CIVILIAN, FixedVotingStrategy(1, 1, 1, True)),
        Player(3, Role.CIVILIAN, FixedVotingStrategy(None, 2, 2, True)),
    ]
    game = Game(players)
    day = game.day_phase(1)
    assert day.eliminated == [1, 2]
    assert not players[1].alive and not players[2].alive
    assert len(day.votes) == 8  # two rounds of voting


def test_tied_candidates_spared_without_majority():
    """No elimination occurs if majority opposes mass elimination."""

    players = [
        Player(0, Role.CIVILIAN, FixedVotingStrategy(1, 1, 1, False)),
        Player(1, Role.CIVILIAN, FixedVotingStrategy(2, 2, 2, False)),
        Player(2, Role.CIVILIAN, FixedVotingStrategy(1, 1, 1, True)),
        Player(3, Role.CIVILIAN, FixedVotingStrategy(None, 2, 2, False)),
    ]
    game = Game(players)
    day = game.day_phase(1)
    assert day.eliminated is None
    assert all(p.alive for p in players)
    assert len(day.votes) == 8


def test_single_nomination_first_day_skips_vote():
    """No voting occurs on the first day if a single player is nominated."""

    players = [
        Player(0, Role.CIVILIAN, NominateAbstainStrategy(1)),
        Player(1, Role.CIVILIAN, AbstainStrategy()),
    ]
    game = Game(players)
    day = game.day_phase(1)
    assert day.votes == []
    assert day.eliminated is None


def test_revote_until_stable_tie():
    """Revotes repeat while ties shrink; stable ties trigger mass vote."""

    players = [
        Player(0, Role.CIVILIAN, MultiRoundStrategy(1, [1, 1, 1], True)),
        Player(1, Role.CIVILIAN, MultiRoundStrategy(2, [2, 2, 2], False)),
        Player(2, Role.CIVILIAN, MultiRoundStrategy(3, [3, 1, 1], False)),
        Player(3, Role.CIVILIAN, MultiRoundStrategy(None, [1, 1, 1], True)),
        Player(4, Role.CIVILIAN, MultiRoundStrategy(None, [2, 2, 2], True)),
        Player(5, Role.CIVILIAN, MultiRoundStrategy(None, [3, 2, 2], True)),
    ]
    game = Game(players)
    day = game.day_phase(1)
    # Three voting rounds: 6 players * 3 rounds = 18 vote records
    assert len(day.votes) == 18
    # Final mass elimination removes players 1 and 2
    assert day.eliminated == [1, 2]
    assert not players[1].alive and not players[2].alive

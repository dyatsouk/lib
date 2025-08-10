import random
from typing import List, Optional

from .actions import SpeechAction, SheriffClaim
class BaseStrategy:
    """Base strategy implementing random behavior.

    This minimal class provides the interface expected by the game engine.
    It stores no state and always chooses randomly among the provided
    options. Subclasses are expected to override the methods relevant to
    their role.
    """

    def speak(self, player, game) -> SpeechAction:
        return SpeechAction()

    def vote(self, player, game, nominations: List[int]) -> Optional[int]:
        return random.choice(nominations) if nominations else None

    # Night actions: subclasses may override
    def sheriff_check(self, player, game, candidates: List[int]) -> Optional[int]:
        return None

    def mafia_kill(self, player, game, candidates: List[int]) -> Optional[int]:
        return None

    def don_check(self, player, game, candidates: List[int]) -> Optional[int]:
        return None

    def last_words(self, player, game) -> SpeechAction:
        return SpeechAction()


class CivilianStrategy(BaseStrategy):
    """Default civilian behaviour.

    The civilian has no persistent state; it randomly nominates and votes
    among the alive players.
    """

    def speak(self, player, game) -> SpeechAction:
        alive = [p.pid for p in game.alive_players if p.pid != player.pid]
        nomination = None
        if alive and random.random() < 0.3:
            nomination = random.choice(alive)
        return SpeechAction(nomination=nomination)


class SheriffStrategy(CivilianStrategy):
    """Basic sheriff implementation performing random checks.

    Attributes
    ----------
    known : dict[int, bool]
        Mapping from player id to whether the checked player is mafia.
    last_check : Optional[int]
        Player id of the most recent night check; used for nominations when
        a mafia member is discovered.
    """

    def __init__(self):
        self.known = {}  # pid -> is_mafia
        self.last_check: Optional[int] = None

    def sheriff_check(self, player, game, candidates: List[int]) -> Optional[int]:
        unknown = [pid for pid in candidates if pid not in self.known]
        if not unknown:
            unknown = candidates
        target = random.choice(unknown)
        return target

    def speak(self, player, game) -> SpeechAction:
        # If we found a mafia, claim and nominate
        mafia_targets = [pid for pid, is_mafia in self.known.items() if is_mafia and game.is_alive(pid)]
        if mafia_targets:
            target = mafia_targets[0]
            claim = SheriffClaim(claimant=player.pid, target=target, is_mafia=True)
            return SpeechAction(nomination=target, claims=[claim])
        return super().speak(player, game)

    def remember(self, target: int, is_mafia: bool):
        self.known[target] = is_mafia
        self.last_check = target

    def vote(self, player, game, nominations: List[int]) -> Optional[int]:
        mafia_targets = [pid for pid in nominations if pid in self.known and self.known[pid]]
        options = mafia_targets or nominations
        return random.choice(options) if options else None


class MafiaStrategy(BaseStrategy):
    """Baseline mafia behaviour targeting civilians.

    Attributes
    ----------
    known_sheriff : Optional[int]
        Player id of the sheriff if discovered; prioritised for elimination.
    """

    def __init__(self):
        self.known_sheriff: Optional[int] = None

    def speak(self, player, game) -> SpeechAction:
        civilians = [p.pid for p in game.alive_players if not p.role.is_mafia()]
        nomination = None
        if civilians and random.random() < 0.3:
            nomination = random.choice(civilians)
        return SpeechAction(nomination=nomination)

    def mafia_kill(self, player, game, candidates: List[int]) -> Optional[int]:
        options = [pid for pid in candidates if not game.get_player(pid).role.is_mafia()]
        if self.known_sheriff and self.known_sheriff in options:
            return self.known_sheriff
        if options:
            return random.choice(options)
        return None

    def vote(self, player, game, nominations: List[int]) -> Optional[int]:
        civilians = [pid for pid in nominations if not game.get_player(pid).role.is_mafia()]
        options = civilians or nominations
        return random.choice(options) if options else None


class DonStrategy(MafiaStrategy):
    """Mafia don strategy that searches for the sheriff at night.

    Attributes
    ----------
    checked : set[int]
        Player ids already investigated to avoid duplicate checks.
    """

    def __init__(self):
        super().__init__()
        self.checked: set[int] = set()

    def don_check(self, player, game, candidates: List[int]) -> Optional[int]:
        options = [pid for pid in candidates if pid not in self.checked]
        if not options:
            options = candidates
        target = random.choice(options)
        return target

    def remember_sheriff(self, pid: int):
        self.known_sheriff = pid


class SingleSheriffCivilianStrategy(BaseStrategy):
    """Civilian behaviour for the SingleSheriff rule set.

    Attributes
    ----------
    sheriff : Optional[int]
        Player id of the first sheriff claimant trusted by the civilian.
    checked_mafia : set[int]
        Players publicly identified as mafia by the sheriff.
    checked_civilians : set[int]
        Players publicly cleared as civilians by the sheriff.
    _processed_speeches : set[int]
        Internal ids of speeches that have already been analysed.
    _next_history_index : int
        Index into the game history indicating the next round to scan for
        claims.
    random_nomination_chance : float
        Base probability of issuing a random nomination when the civilian has
        no guidance from the sheriff.

    The strategy fully trusts the first sheriff claim it hears. Once the
    sheriff is revealed, civilians mirror the sheriff's nomination and vote
    unless they themselves are the target. The strategy tracks the sheriff's
    public checks and avoids nominating or voting for confirmed civilians
    while prioritising confirmed mafia. To keep processing cheap we remember
    which speeches have already been analysed.
    """

    def __init__(self, random_nomination_chance: float = 0.3):
        """Initialise the strategy.

        Parameters
        ----------
        random_nomination_chance : float, optional
            Probability of nominating a random player when no sheriff
            information is available, by default ``0.3``.
        """

        self.sheriff: Optional[int] = None
        self.checked_mafia: set[int] = set()
        self.checked_civilians: set[int] = set()
        self._processed_speeches: set[int] = set()
        self._next_history_index = 0
        # Allow simulations to tune how often civilians nominate at random
        # when they have no better information.
        self.random_nomination_chance = random_nomination_chance

    def _update_claims(self, game):
        """Incorporate new sheriff claims from past and current speeches."""
        while self._next_history_index < len(game.history):
            round_log = game.history[self._next_history_index]
            for speech in round_log.day.speeches:
                if id(speech) not in self._processed_speeches:
                    self._process_speech(speech)
            self._next_history_index += 1
        for speech in getattr(game, "current_speeches", []):
            if id(speech) not in self._processed_speeches:
                self._process_speech(speech)

    def _process_speech(self, speech):
        for claim in speech.action.claims:
            if self.sheriff is None:
                self.sheriff = claim.claimant
            if claim.claimant == self.sheriff:
                if claim.is_mafia:
                    self.checked_mafia.add(claim.target)
                else:
                    self.checked_civilians.add(claim.target)
        self._processed_speeches.add(id(speech))

    def speak(self, player, game) -> SpeechAction:
        """Return a speech aligning with trusted sheriff information."""

        self._update_claims(game)

        # Prioritise nominating mafia that the sheriff has publicly checked.
        for target in self.checked_mafia:
            if target != player.pid and game.is_alive(target):
                return SpeechAction(nomination=target)

        if self.sheriff is not None:
            # If the sheriff has spoken this round, mirror their nomination
            # unless they nominated us.
            sheriff_speech = next(
                (s for s in game.current_speeches if s.speaker == self.sheriff),
                None,
            )
            if (
                sheriff_speech
                and sheriff_speech.action.nomination is not None
                and sheriff_speech.action.nomination != player.pid
            ):
                return SpeechAction(nomination=sheriff_speech.action.nomination)

        # Otherwise pick randomly among alive players that are not cleared,
        # excluding the sheriff himself.
        alive = [
            p.pid
            for p in game.alive_players
            if p.pid != player.pid and p.pid not in self.checked_civilians
        ]
        if self.sheriff is not None and self.sheriff in alive:
            alive.remove(self.sheriff)
        nomination = None
        # ``random_nomination_chance`` keeps the game dynamic by allowing
        # occasional uninformed nominations.  It can be customised when the
        # strategy is constructed to explore different civilian behaviours.
        if alive and random.random() < self.random_nomination_chance:
            nomination = random.choice(alive)
        return SpeechAction(nomination=nomination)

    def vote(self, player, game, nominations: List[int]) -> Optional[int]:
        """Choose a vote, mirroring the sheriff when possible."""

        self._update_claims(game)
        if self.sheriff is not None:
            sheriff_speech = next(
                (s for s in game.current_speeches if s.speaker == self.sheriff),
                None,
            )
            if (
                sheriff_speech
                and sheriff_speech.action.nomination is not None
                and sheriff_speech.action.nomination != player.pid
                and sheriff_speech.action.nomination in nominations
            ):
                return sheriff_speech.action.nomination
        mafia_targets = [
            pid
            for pid in nominations
            if pid in self.checked_mafia and pid != player.pid
        ]
        options = mafia_targets or [
            pid
            for pid in nominations
            if pid not in self.checked_civilians and pid != player.pid
        ]
        return random.choice(options) if options else None


class SingleSheriffSheriffStrategy(SheriffStrategy):
    """Sheriff strategy for the SingleSheriff rule set.

    Attributes
    ----------
    reveal_probability : float
        Chance of publicly revealing the role each day while still hidden.
    revealed : bool
        Whether the sheriff has already announced himself.

    Each day the sheriff decides randomly whether to reveal himself based on
    ``reveal_probability``. Once revealed he will continue to speak openly and
    share all gathered checks. Regardless of being revealed or not, when the
    sheriff dies he publishes all check results in his last words.
    """

    def __init__(self, reveal_probability: float = 0.5):
        super().__init__()
        self.reveal_probability = reveal_probability
        self.revealed = False

    def speak(self, player, game) -> SpeechAction:
        # If still hidden, decide this round whether to reveal
        if not self.revealed and random.random() < self.reveal_probability:
            self.revealed = True
        if self.revealed:
            claims = [
                SheriffClaim(claimant=player.pid, target=t, is_mafia=res)
                for t, res in self.known.items()
            ]
            nomination = (
                self.last_check
                if self.last_check in self.known and self.known[self.last_check]
                else None
            )
            return SpeechAction(nomination=nomination, claims=claims)
        return CivilianStrategy.speak(self, player, game)

    def last_words(self, player, game) -> SpeechAction:
        claims = [
            SheriffClaim(claimant=player.pid, target=t, is_mafia=res)
            for t, res in self.known.items()
        ]
        return SpeechAction(claims=claims)

    def vote(self, player, game, nominations: List[int]) -> Optional[int]:
        if self.revealed:
            mafia_targets = [pid for pid in nominations if pid in self.known and self.known[pid]]
            options = mafia_targets or nominations
            return random.choice(options) if options else None
        return CivilianStrategy.vote(self, player, game, nominations)


class SingleSheriffMafiaStrategy(MafiaStrategy):
    """Mafia behaviour tailored for the SingleSheriff strategies.

    Attributes
    ----------
    claimed_sheriff : Optional[int]
        Player id of the first claimant to the sheriff role.
    kill_queue : List[int]
        Ordered list of civilians publicly cleared by the sheriff.
    _processed_speeches : set[int]
        Cache of processed speech ids to avoid re-scanning history.
    _next_history_index : int
        Index of the next round in the game history to process.
    known_sheriff : Optional[int]
        Inherited from :class:`MafiaStrategy`; real sheriff if discovered by the
        don.

    The mafia prioritise killing a known or claimed sheriff and afterwards any
    civilians confirmed by the sheriff. To avoid repeatedly scanning the entire
    history we cache processed speeches.
    """

    def __init__(self):
        super().__init__()
        self.claimed_sheriff: Optional[int] = None
        self.kill_queue: List[int] = []
        self._processed_speeches: set[int] = set()
        self._next_history_index = 0

    def _update_claims(self, game):
        while self._next_history_index < len(game.history):
            round_log = game.history[self._next_history_index]
            for speech in round_log.day.speeches:
                if id(speech) not in self._processed_speeches:
                    self._process_speech(speech)
            self._next_history_index += 1
        for speech in getattr(game, "current_speeches", []):
            if id(speech) not in self._processed_speeches:
                self._process_speech(speech)

    def _process_speech(self, speech):
        for claim in speech.action.claims:
            if self.claimed_sheriff is None and self.known_sheriff is None:
                self.claimed_sheriff = claim.claimant
            if claim.claimant == self.claimed_sheriff or claim.claimant == self.known_sheriff:
                if not claim.is_mafia and claim.target not in self.kill_queue:
                    self.kill_queue.append(claim.target)
        self._processed_speeches.add(id(speech))

    def mafia_kill(self, player, game, candidates: List[int]) -> Optional[int]:
        self._update_claims(game)
        self.kill_queue = [pid for pid in self.kill_queue if game.is_alive(pid)]
        options = [pid for pid in candidates if not game.get_player(pid).role.is_mafia()]
        if self.known_sheriff is not None and self.known_sheriff in options:
            return self.known_sheriff
        if self.claimed_sheriff is not None and self.claimed_sheriff in options:
            return self.claimed_sheriff
        if self.kill_queue:
            target = self.kill_queue.pop(0)
            if target in options:
                return target
        if options:
            return random.choice(options)
        return None


class SingleSheriffDonStrategy(SingleSheriffMafiaStrategy):
    """Don variant of the SingleSheriff mafia strategy.

    Attributes
    ----------
    checked : set[int]
        Player ids already investigated at night.

    Behaves like :class:`SingleSheriffMafiaStrategy` but keeps track of players
    already checked at night to avoid redundant investigations.
    """

    def __init__(self):
        super().__init__()
        self.checked: set[int] = set()

    def don_check(self, player, game, candidates: List[int]) -> Optional[int]:
        options = [pid for pid in candidates if pid not in self.checked]
        if not options:
            options = candidates
        target = random.choice(options)
        return target

import random
from typing import List, Optional

from .actions import SpeechAction, SheriffClaim
from .roles import Role


class BaseStrategy:
    """Base strategy implementing random behavior."""

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


class CivilianStrategy(BaseStrategy):
    def speak(self, player, game) -> SpeechAction:
        alive = [p.pid for p in game.alive_players if p.pid != player.pid]
        nomination = None
        if alive and random.random() < 0.3:
            nomination = random.choice(alive)
        return SpeechAction(nomination=nomination)


class SheriffStrategy(CivilianStrategy):
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
            return SpeechAction(nomination=target, claim=claim)
        return super().speak(player, game)

    def remember(self, target: int, is_mafia: bool):
        self.known[target] = is_mafia
        self.last_check = target

    def vote(self, player, game, nominations: List[int]) -> Optional[int]:
        mafia_targets = [pid for pid in nominations if pid in self.known and self.known[pid]]
        options = mafia_targets or nominations
        return random.choice(options) if options else None


class MafiaStrategy(BaseStrategy):
    def __init__(self):
        self.known_sheriff: Optional[int] = None

    def speak(self, player, game) -> SpeechAction:
        civilians = [p.pid for p in game.alive_players if not p.role.is_mafia()]
        nomination = None
        if civilians and random.random() < 0.3:
            nomination = random.choice(civilians)
        return SpeechAction(nomination=nomination)

    def mafia_kill(self, player, game, candidates: List[int]) -> Optional[int]:
        if self.known_sheriff and self.known_sheriff in candidates:
            return self.known_sheriff
        return random.choice(candidates)

    def vote(self, player, game, nominations: List[int]) -> Optional[int]:
        civilians = [pid for pid in nominations if not game.get_player(pid).role.is_mafia()]
        options = civilians or nominations
        return random.choice(options) if options else None


class DonStrategy(MafiaStrategy):
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

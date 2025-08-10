import random
from typing import List, Optional

from .roles import Role
from .player import Player
from .actions import (
    SpeechAction,
    Vote,
    CheckResult,
    DonCheckResult,
    DayLog,
    NightLog,
    RoundLog,
)


class Game:
    def __init__(self, players: List[Player]):
        self.players = players
        self.history: List[RoundLog] = []

    # Helper methods
    def get_player(self, pid: int) -> Player:
        return self.players[pid]

    @property
    def alive_players(self) -> List[Player]:
        return [p for p in self.players if p.alive]

    def is_alive(self, pid: int) -> bool:
        return self.players[pid].alive

    def mafia_count(self) -> int:
        return sum(1 for p in self.alive_players if p.role.is_mafia())

    def civilian_count(self) -> int:
        return sum(1 for p in self.alive_players if p.role.is_civilian())

    def check_win(self) -> Optional[Role]:
        if self.mafia_count() == 0:
            return Role.CIVILIAN
        if self.mafia_count() >= self.civilian_count():
            return Role.MAFIA
        return None

    def run(self) -> Role:
        round_no = 1
        while True:
            day_log = self.day_phase()
            winner = self.check_win()
            night_log = None
            if not winner:
                night_log = self.night_phase()
                winner = self.check_win()
            self.history.append(RoundLog(day=day_log, night=night_log))
            if winner:
                return winner
            round_no += 1

    # Day phase
    def day_phase(self) -> DayLog:
        speeches = {}
        nominations = []
        for player in list(self.alive_players):
            action: SpeechAction = player.speak(self)
            speeches[player.pid] = action
            if action.nomination is not None and self.is_alive(action.nomination):
                if action.nomination not in nominations:
                    nominations.append(action.nomination)
        votes = []
        vote_counts = {pid: 0 for pid in nominations}
        for player in self.alive_players:
            vote_target = player.vote(self, nominations)
            votes.append(Vote(voter=player.pid, target=vote_target))
            if vote_target in vote_counts:
                vote_counts[vote_target] += 1
        eliminated = None
        if vote_counts:
            max_votes = max(vote_counts.values())
            top = [pid for pid, count in vote_counts.items() if count == max_votes]
            if len(top) == 1:
                eliminated = top[0]
                self.players[eliminated].alive = False
        return DayLog(speeches=speeches, votes=votes, eliminated=eliminated)

    # Night phase
    def night_phase(self) -> NightLog:
        sheriff_check = None
        don_check = None
        kill = None

        # Sheriff check
        sheriffs = [p for p in self.alive_players if p.role == Role.SHERIFF]
        if sheriffs:
            sheriff = sheriffs[0]
            candidates = [p.pid for p in self.alive_players if p.pid != sheriff.pid]
            target = sheriff.sheriff_check(self, candidates)
            if target is not None and self.is_alive(target):
                target_player = self.get_player(target)
                result = target_player.role.is_mafia()
                sheriff.strategy.remember(target, result)  # type: ignore
                sheriff_check = CheckResult(checker=sheriff.pid, target=target, is_mafia=result)

        # Don check
        dons = [p for p in self.alive_players if p.role == Role.DON]
        if dons:
            don = dons[0]
            candidates = [p.pid for p in self.alive_players if p.pid != don.pid]
            target = don.don_check(self, candidates)
            if target is not None and self.is_alive(target):
                is_sheriff = self.get_player(target).role == Role.SHERIFF
                don.strategy.checked.add(target)  # type: ignore
                if is_sheriff:
                    for mafia in self.alive_players:
                        if mafia.role.is_mafia():
                            mafia.strategy.known_sheriff = target  # type: ignore
                don_check = DonCheckResult(checker=don.pid, target=target, is_sheriff=is_sheriff)

        # Mafia kill
        mafia_players = [p for p in self.alive_players if p.role.is_mafia()]
        if mafia_players:
            candidates = [p.pid for p in self.alive_players if not p.role.is_mafia()]
            suggestions = [m.mafia_kill(self, candidates) for m in mafia_players]
            suggestions = [s for s in suggestions if s is not None]
            if suggestions:
                kill = max(set(suggestions), key=suggestions.count)
                if self.is_alive(kill):
                    self.get_player(kill).alive = False
        return NightLog(sheriff_check=sheriff_check, don_check=don_check, kill=kill)

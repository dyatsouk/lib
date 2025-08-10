import random
from typing import List, Optional

from .roles import Role
from .player import Player
from .logger import GameLogger
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
    def __init__(self, players: List[Player], logger: Optional[GameLogger] = None):
        self.players = players
        self.history: List[RoundLog] = []
        self.logger = logger
        self.day_start_pid = 0

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
            day_log = self.day_phase(round_no)
            winner = self.check_win()
            night_log = None
            if not winner:
                night_log = self.night_phase(round_no)
                winner = self.check_win()
            self.history.append(RoundLog(day=day_log, night=night_log))
            if winner:
                return winner
            round_no += 1

    # Day phase
    def day_phase(self, day_no: int) -> DayLog:
        if self.logger:
            self.logger.log(f"day {day_no}")
        speeches = {}
        nominations = []
        alive = self.alive_players
        start_index = 0
        for i, p in enumerate(alive):
            if p.pid >= self.day_start_pid:
                start_index = i
                break
        ordered_players = alive[start_index:] + alive[:start_index]
        for player in ordered_players:
            action: SpeechAction = player.speak(self)
            speeches[player.pid] = action
            if action.nomination is not None and self.is_alive(action.nomination):
                if action.nomination not in nominations:
                    nominations.append(action.nomination)
                if self.logger:
                    self.logger.log(
                        f"player {player.pid + 1} nominates player {action.nomination + 1}"
                    )
            if action.claim is not None and self.logger:
                claim = action.claim
                self.logger.log(
                    f"player {claim.claimant + 1} claims {claim.target + 1} is mafia"
                )
        votes = []
        vote_counts = {pid: 0 for pid in nominations}
        if self.logger:
            self.logger.log(f"day {day_no} voting")
        for player in self.alive_players:
            vote_target = player.vote(self, nominations)
            votes.append(Vote(voter=player.pid, target=vote_target))
            if vote_target in vote_counts:
                vote_counts[vote_target] += 1
            if self.logger:
                if vote_target is not None:
                    self.logger.log(
                        f"player {player.pid + 1} votes for player {vote_target + 1}"
                    )
                else:
                    self.logger.log(f"player {player.pid + 1} abstains")
        eliminated = None
        if vote_counts:
            max_votes = max(vote_counts.values())
            top = [pid for pid, count in vote_counts.items() if count == max_votes]
            if len(top) == 1:
                eliminated = top[0]
                self.players[eliminated].alive = False
        if self.logger:
            if eliminated is not None:
                self.logger.log(f"player {eliminated + 1} is eliminated")
            else:
                self.logger.log("no elimination")
        # determine next day's starting player
        if ordered_players:
            next_pid = ordered_players[0].pid + 1
            alive_after = [p for p in self.players if p.alive and p.pid >= next_pid]
            if alive_after:
                self.day_start_pid = alive_after[0].pid
            else:
                self.day_start_pid = next((p.pid for p in self.players if p.alive), 0)
        return DayLog(speeches=speeches, votes=votes, eliminated=eliminated)

    # Night phase
    def night_phase(self, night_no: int) -> NightLog:
        if self.logger:
            self.logger.log(f"night {night_no}")
        sheriff_check = None
        don_check = None
        kill = None

        # Mafia kill happens first
        mafia_players = [p for p in self.alive_players if p.role.is_mafia()]
        if mafia_players:
            candidates = [p.pid for p in self.alive_players]
            don = next((p for p in mafia_players if p.role == Role.DON), None)
            if don:
                kill = don.mafia_kill(self, candidates)
            else:
                suggestions = [m.mafia_kill(self, candidates) for m in mafia_players]
                suggestions = [s for s in suggestions if s is not None]
                if suggestions:
                    kill = max(set(suggestions), key=suggestions.count)
            if kill is not None and self.is_alive(kill):
                self.get_player(kill).alive = False
                if self.logger:
                    self.logger.log(f"mafia kill player {kill + 1}")
            elif self.logger:
                self.logger.log("mafia kill failed")

        # Don check after the kill
        don = next((p for p in self.alive_players if p.role == Role.DON), None)
        if don:
            candidates = [p.pid for p in self.players if p.pid != don.pid]
            target = don.don_check(self, candidates)
            if target is not None:
                is_sheriff = self.get_player(target).role == Role.SHERIFF
                don.strategy.checked.add(target)  # type: ignore
                if is_sheriff:
                    for mafia in self.alive_players:
                        if mafia.role.is_mafia():
                            mafia.strategy.known_sheriff = target  # type: ignore
                don_check = DonCheckResult(checker=don.pid, target=target, is_sheriff=is_sheriff)
                if self.logger:
                    result = "is" if is_sheriff else "is not"
                    self.logger.log(
                        f"don checks player {target + 1}: {result} sheriff"
                    )

        # Sheriff check last
        sheriff = next((p for p in self.alive_players if p.role == Role.SHERIFF), None)
        if sheriff:
            candidates = [p.pid for p in self.players if p.pid != sheriff.pid]
            target = sheriff.sheriff_check(self, candidates)
            if target is not None:
                result = self.get_player(target).role.is_mafia()
                sheriff.strategy.remember(target, result)  # type: ignore
                sheriff_check = CheckResult(checker=sheriff.pid, target=target, is_mafia=result)
                if self.logger:
                    res = "mafia" if result else "not mafia"
                    self.logger.log(
                        f"sheriff checks player {target + 1}: {res}"
                    )

        return NightLog(sheriff_check=sheriff_check, don_check=don_check, kill=kill)

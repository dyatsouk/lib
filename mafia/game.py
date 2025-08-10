import random
from typing import List, Optional

from .roles import Role
from .player import Player
from .logger import GameLogger
from .actions import (
    SpeechAction,
    SpeechLog,
    Vote,
    CheckResult,
    DonCheckResult,
    DayLog,
    NightLog,
    RoundLog,
)

class Game:
    """Main game engine coordinating day and night cycles."""

    def __init__(self, players: List[Player], logger: Optional[GameLogger] = None):
        self.players = players
        self.history: List[RoundLog] = []
        self.logger = logger
        self.day_start_pid = 0
        self.current_speeches: List[SpeechLog] = []

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
        if self.logger:
            mafia_players = [p.pid + 1 for p in self.players if p.role == Role.MAFIA]
            don_player = next(p.pid + 1 for p in self.players if p.role == Role.DON)
            sheriff_player = next(p.pid + 1 for p in self.players if p.role == Role.SHERIFF)
            mafia_list = ", ".join(str(pid) for pid in mafia_players)
            self.logger.log(f"mafia: {mafia_list}")
            self.logger.log(f"don: {don_player}")
            self.logger.log(f"sheriff: {sheriff_player}")
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
        """Run speeches, nominations and voting for a single day.

        Handles two-stage tie resolution: if the first vote ties, a revote is
        held among the tied candidates. Should the revote also tie, players
        vote on eliminating all tied candidates and an absolute majority is
        required to remove them.
        """

        if self.logger:
            self.logger.log(f"day {day_no}")
        speeches = []
        nominations = []
        self.current_speeches = []

        # Morning speech from last night's victim
        last_kill = None
        if self.history and self.history[-1].night and self.history[-1].night.kill is not None:
            last_kill = self.history[-1].night.kill
        if last_kill is not None:
            victim = self.get_player(last_kill)
            action = victim.last_words(self)
            action.nomination = None
            speech = SpeechLog(speaker=victim.pid, action=action)
            speeches.append(speech)
            self.current_speeches.append(speech)
            if self.logger:
                if action.claims:
                    for claim in action.claims:
                        res = "mafia" if claim.is_mafia else "not mafia"
                        self.logger.log(
                            f"player {claim.claimant + 1} claims {claim.target + 1} is {res}"
                        )
                else:
                    self.logger.log(f"player {victim.pid + 1} has no claims")

        alive = self.alive_players
        start_index = 0
        for i, p in enumerate(alive):
            if p.pid >= self.day_start_pid:
                start_index = i
                break
        ordered_players = alive[start_index:] + alive[:start_index]
        for player in ordered_players:
            action: SpeechAction = player.speak(self)
            speech = SpeechLog(speaker=player.pid, action=action)
            speeches.append(speech)
            self.current_speeches.append(speech)
            if action.nomination is not None and self.is_alive(action.nomination):
                if action.nomination not in nominations:
                    nominations.append(action.nomination)
                if self.logger:
                    self.logger.log(
                        f"player {player.pid + 1} nominates player {action.nomination + 1}"
                    )
            if action.claims and self.logger:
                for claim in action.claims:
                    res = "mafia" if claim.is_mafia else "not mafia"
                    self.logger.log(
                        f"player {claim.claimant + 1} claims {claim.target + 1} is {res}"
                    )
        votes = []
        vote_counts = {pid: 0 for pid in nominations}
        if self.logger:
            self.logger.log(f"day {day_no} voting")
        for player in self.alive_players:
            vote_target = player.vote(self, nominations)
            if nominations:
                # Force a valid vote choice; abstaining defaults to the last nomination.
                if vote_target not in nominations:
                    vote_target = nominations[-1]
                votes.append(Vote(voter=player.pid, target=vote_target))
                vote_counts[vote_target] += 1
                if self.logger:
                    self.logger.log(
                        f"player {player.pid + 1} votes for player {vote_target + 1}"
                    )
            else:
                # No nominations: players effectively abstain.
                votes.append(Vote(voter=player.pid, target=None))
                if self.logger:
                    self.logger.log(f"player {player.pid + 1} abstains")

        eliminated: List[int] = []
        if vote_counts:
            max_votes = max(vote_counts.values())
            top = [pid for pid, count in vote_counts.items() if count == max_votes]
            if len(top) == 1:
                eliminated = top
            else:
                # Re-run voting with only the tied candidates.
                # Every player votes again exactly once.
                if self.logger:
                    self.logger.log("tie detected, revoting")
                revote_counts = {pid: 0 for pid in top}
                for player in self.alive_players:
                    vote_target = player.vote(self, top)
                    if vote_target not in top:
                        # Abstention in revote still defaults to the last candidate.
                        vote_target = top[-1]
                    votes.append(Vote(voter=player.pid, target=vote_target))
                    revote_counts[vote_target] += 1
                    if self.logger:
                        self.logger.log(
                            f"player {player.pid + 1} revotes for player {vote_target + 1}"
                        )
                max_votes = max(revote_counts.values())
                top = [pid for pid, count in revote_counts.items() if count == max_votes]
                if len(top) == 1:
                    eliminated = top
                else:
                    # Final vote: should all tied players be eliminated?
                    # Absolute majority of "yes" votes eliminates them.
                    if self.logger:
                        self.logger.log("revote tie, voting on elimination")
                    yes_votes = sum(
                        1 for p in self.alive_players if p.vote_elimination(self, top)
                    )
                    if yes_votes > len(self.alive_players) // 2:
                        eliminated = top

        if eliminated:
            for pid in eliminated:
                self.players[pid].alive = False
            if self.logger:
                if len(eliminated) == 1:
                    self.logger.log(f"player {eliminated[0] + 1} is eliminated")
                else:
                    elim_str = ", ".join(str(pid + 1) for pid in eliminated)
                    self.logger.log(f"players {elim_str} are eliminated")
        else:
            if self.logger:
                self.logger.log("no elimination")

        # Eliminated players' last words in the order they were nominated.
        if eliminated:
            for pid in eliminated:  # order preserved from vote_counts
                player = self.get_player(pid)
                action = player.last_words(self)
                action.nomination = None
                speech = SpeechLog(speaker=player.pid, action=action)
                speeches.append(speech)
                self.current_speeches.append(speech)
                if action.claims and self.logger:
                    for claim in action.claims:
                        res = "mafia" if claim.is_mafia else "not mafia"
                        self.logger.log(
                            f"player {claim.claimant + 1} claims {claim.target + 1} is {res}"
                        )

        # determine next day's starting player
        if ordered_players:
            next_pid = ordered_players[0].pid + 1
            alive_after = [p for p in self.players if p.alive and p.pid >= next_pid]
            if alive_after:
                self.day_start_pid = alive_after[0].pid
            else:
                self.day_start_pid = next((p.pid for p in self.players if p.alive), 0)
        return DayLog(
            speeches=speeches, votes=votes, eliminated=eliminated or None
        )

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
                victim = self.get_player(kill)
                if victim.role == Role.SHERIFF:
                    # Sheriff remains alive until the end of the night to perform a final check
                    pass
                else:
                    victim.alive = False
                if self.logger:
                    self.logger.log(f"mafia kill player {kill + 1}")
            elif self.logger:
                self.logger.log("mafia kill failed")

        # Don check after the kill
        don = next((p for p in self.alive_players if p.role == Role.DON), None)
        if don:
            candidates = [p.pid for p in self.players if p.pid != don.pid and p.pid != kill]
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
            candidates = [p.pid for p in self.players if p.pid != sheriff.pid and p.pid != kill]
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

        # Apply delayed kill (sheriff remains alive for the check)
        if kill is not None and self.is_alive(kill):
            self.get_player(kill).alive = False

        return NightLog(sheriff_check=sheriff_check, don_check=don_check, kill=kill)

    # History access
    def history_for(self, pid: int) -> List[RoundLog]:
        """Return the portion of game history observable to the given player."""
        player = self.get_player(pid)
        visible: List[RoundLog] = []
        for round_log in self.history:
            day = round_log.day
            night = None
            if round_log.night:
                night = NightLog(
                    sheriff_check=None,
                    don_check=None,
                    kill=round_log.night.kill,
                )
                if (
                    player.role == Role.SHERIFF
                    and round_log.night.sheriff_check
                ):
                    night.sheriff_check = round_log.night.sheriff_check
                if (
                    player.role == Role.DON
                    and round_log.night.don_check
                ):
                    night.don_check = round_log.night.don_check
            visible.append(RoundLog(day=day, night=night))
        return visible

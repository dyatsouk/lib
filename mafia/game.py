import random
from typing import Callable, List, Optional

from .roles import Role
from .player import Player
from .events import EventDispatcher
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
    """Main game engine coordinating day and night cycles.

    The engine emits events via :class:`~mafia.events.EventDispatcher` instead
    of writing to a logger directly.  This allows external observers to attach
    custom loggers or analytics without modifying the game logic.
    """

    def __init__(self, players: List[Player], dispatcher: EventDispatcher | None = None):
        self.players = players
        self.history: List[RoundLog] = []
        self.dispatcher = dispatcher or EventDispatcher()
        self.day_start_pid = 0
        self.current_speeches: List[SpeechLog] = []
        # Callbacks fired whenever a new speech is added.  Strategies that
        # analyse claims can subscribe to this signal to update their internal
        # state only when necessary instead of scanning the entire history on
        # every action.
        self._speech_listeners: List[Callable[[int, int, SpeechLog], None]] = []
        for player in players:
            callback = getattr(player.strategy, "on_speech", None)
            if callable(callback):
                self._speech_listeners.append(callback)

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

    # Event system -----------------------------------------------------
    def add_speech_listener(self, callback: Callable[[int, int, SpeechLog], None]):
        """Register a callback invoked whenever a speech is added."""

        self._speech_listeners.append(callback)

    def _notify_speech(self, day_no: int, index: int, speech: SpeechLog):
        """Emit a speech event to all listeners.

        Parameters
        ----------
        day_no:
            Current day number, starting at ``1``.
        index:
            Zero-based index of the speech within the day.  Listeners may cache
            this information to skip reprocessing already-seen speeches.
        speech:
            The newly recorded :class:`~mafia.actions.SpeechLog` instance.
        """

        for callback in self._speech_listeners:
            callback(day_no, index, speech)
        # Publish structured event for external observers
        self.dispatcher.emit("speech_added", day=day_no, index=index, speech=speech)

    # Convenience for tests and manual injection -----------------------
    def add_speech(self, speech: SpeechLog, day_no: int = 1):
        """Append ``speech`` to ``current_speeches`` and fire callbacks.

        This helper allows tests to simulate new speeches without running an
        entire day phase.
        """

        self.current_speeches.append(speech)
        self._notify_speech(day_no, len(self.current_speeches) - 1, speech)

    def run(self) -> Role:
        mafia_players = [p.pid for p in self.players if p.role == Role.MAFIA]
        don_player = next(p.pid for p in self.players if p.role == Role.DON)
        sheriff_player = next(p.pid for p in self.players if p.role == Role.SHERIFF)
        self.dispatcher.emit(
            "game_started", mafia=mafia_players, don=don_player, sheriff=sheriff_player
        )
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

        self.dispatcher.emit("day_started", day=day_no)
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
            self.add_speech(speech, day_no)
            # Claims are reported via the speech_added event

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
            self.add_speech(speech, day_no)
            if action.nomination is not None and self.is_alive(action.nomination):
                if action.nomination not in nominations:
                    nominations.append(action.nomination)
                # Nomination details are conveyed through speech_added event
            # Claims are reported via speech_added event
        votes: List[Vote] = []
        eliminated: List[int] = []

        # Rule 4.4.10: skip voting on the first day if only one nomination exists.
        if not (day_no == 1 and len(nominations) == 1):
            current_candidates = list(nominations)
            previous_candidates: Optional[List[int]] = None

            while current_candidates:
                vote_counts = {pid: 0 for pid in current_candidates}
                self.dispatcher.emit("info", message=f"day {day_no} voting")
                for player in self.alive_players:
                    vote_target = player.vote(self, current_candidates)
                    if current_candidates:
                        # Force a valid vote choice; abstaining defaults to the last
                        # candidate.
                        if vote_target not in current_candidates:
                            vote_target = current_candidates[-1]
                        votes.append(Vote(voter=player.pid, target=vote_target))
                        vote_counts[vote_target] += 1
                        self.dispatcher.emit(
                            "vote_cast", day=day_no, voter=player.pid, target=vote_target
                        )
                    else:
                        # No nominations: players effectively abstain.
                        votes.append(Vote(voter=player.pid, target=None))
                        self.dispatcher.emit(
                            "vote_cast", day=day_no, voter=player.pid, target=None
                        )

                if not vote_counts:
                    break
                max_votes = max(vote_counts.values())
                top = [pid for pid, count in vote_counts.items() if count == max_votes]
                if len(top) == 1:
                    eliminated = top
                    break

                # Rule 4.4.12: tied players get extra speeches and a revote.
                self.dispatcher.emit("info", message="tie detected, revoting")
                for pid in nominations:
                    if pid in top:
                        # Extra 30-second speech; nominations during this phase are
                        # ignored per tournament rules.
                        player = self.get_player(pid)
                        action = player.speak(self)
                        action.nomination = None
                        speech = SpeechLog(speaker=player.pid, action=action)
                        speeches.append(speech)
                        self.add_speech(speech, day_no)
                        if action.claims:
                            pass  # claims handled by speech_added event

                if previous_candidates and set(top) == set(previous_candidates):
                    # Rule 4.4.12.3: if the same set ties again, vote on eliminating all.
                    self.dispatcher.emit(
                        "info", message="revote tie, voting on elimination"
                    )
                    yes_votes = sum(
                        1 for p in self.alive_players if p.vote_elimination(self, top)
                    )
                    if yes_votes > len(self.alive_players) // 2:
                        eliminated = top
                    break

                # Rule 4.4.12.2: if tie narrows to fewer candidates, repeat.
                previous_candidates = top
                current_candidates = top

        if eliminated:
            for pid in eliminated:
                self.players[pid].alive = False
            self.dispatcher.emit("players_eliminated", day=day_no, players=eliminated)
        else:
            self.dispatcher.emit("no_elimination", day=day_no)

        # Eliminated players' last words in the order they were nominated.
        if eliminated:
            for pid in eliminated:  # order preserved from vote_counts
                player = self.get_player(pid)
                action = player.last_words(self)
                action.nomination = None
                speech = SpeechLog(speaker=player.pid, action=action)
                speeches.append(speech)
                self.add_speech(speech, day_no)
                if action.claims:
                    pass  # claims handled by speech_added event

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
        self.dispatcher.emit("night_started", night=night_no)
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
                self.dispatcher.emit(
                    "night_action",
                    night=night_no,
                    action="mafia_kill",
                    target=kill,
                    success=True,
                )
            else:
                self.dispatcher.emit(
                    "night_action",
                    night=night_no,
                    action="mafia_kill",
                    target=kill,
                    success=False,
                )
        else:
            self.dispatcher.emit(
                "night_action",
                night=night_no,
                action="mafia_kill",
                target=None,
                success=False,
            )

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
                self.dispatcher.emit(
                    "night_action",
                    night=night_no,
                    action="don_check",
                    checker=don.pid,
                    target=target,
                    is_sheriff=is_sheriff,
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
                self.dispatcher.emit(
                    "night_action",
                    night=night_no,
                    action="sheriff_check",
                    checker=sheriff.pid,
                    target=target,
                    is_mafia=result,
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

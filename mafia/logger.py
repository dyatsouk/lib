from __future__ import annotations

"""Event driven logger for :class:`mafia.game.Game`.

The logger subscribes to events published by an
:class:`~mafia.events.EventDispatcher` and renders them as human readable
messages.  It can optionally print to stdout and/or write to a file.
"""

from typing import Iterable, List

from .events import EventDispatcher


class GameLogger:
    """Listener that records :class:`mafia.game.Game` events."""

    def __init__(self, verbose: bool = False, log_to_file: bool = False, filename: str = "simul.log"):
        self.verbose = verbose
        self.file = open(filename, "w") if log_to_file else None

    # ------------------------------------------------------------------
    # Subscription
    def attach(self, dispatcher: EventDispatcher) -> None:
        """Subscribe to all game related events on ``dispatcher``."""

        dispatcher.subscribe("info", self.log)
        dispatcher.subscribe("day_started", lambda day: self.log(f"day {day}"))
        dispatcher.subscribe("night_started", lambda night: self.log(f"night {night}"))
        dispatcher.subscribe("speech_added", self._on_speech)
        dispatcher.subscribe("vote_cast", self._on_vote)
        dispatcher.subscribe("night_action", self._on_night)
        dispatcher.subscribe("players_eliminated", self._on_eliminated)
        dispatcher.subscribe("no_elimination", lambda day: self.log("no elimination"))
        dispatcher.subscribe("game_started", self._on_game_start)

    # Handlers ---------------------------------------------------------
    def _on_game_start(self, mafia: List[int], don: int, sheriff: int) -> None:
        mafia_list = ", ".join(str(pid + 1) for pid in mafia)
        self.log(f"mafia: {mafia_list}")
        self.log(f"don: {don + 1}")
        self.log(f"sheriff: {sheriff + 1}")

    def _on_speech(self, day: int, index: int, speech) -> None:
        """Render speeches, nominations and claims."""

        if speech.action.nomination is not None:
            self.log(
                f"player {speech.speaker + 1} nominates player {speech.action.nomination + 1}"
            )
        if speech.action.claims:
            for claim in speech.action.claims:
                res = "mafia" if claim.is_mafia else "not mafia"
                self.log(
                    f"player {claim.claimant + 1} claims {claim.target + 1} is {res}"
                )
        else:
            self.log(f"player {speech.speaker + 1} has no claims")

    def _on_vote(self, day: int, voter: int, target: int | None) -> None:
        if target is None:
            self.log(f"player {voter + 1} abstains")
        else:
            self.log(f"player {voter + 1} votes for player {target + 1}")

    def _on_night(self, night: int, action: str, **payload) -> None:
        if action == "mafia_kill":
            if payload.get("success") and payload.get("target") is not None:
                self.log(f"mafia kill player {payload['target'] + 1}")
            else:
                self.log("mafia kill failed")
        elif action == "don_check":
            result = "is" if payload.get("is_sheriff") else "is not"
            self.log(
                f"don checks player {payload['target'] + 1}: {result} sheriff"
            )
        elif action == "sheriff_check":
            res = "mafia" if payload.get("is_mafia") else "not mafia"
            self.log(
                f"sheriff checks player {payload['target'] + 1}: {res}"
            )

    def _on_eliminated(self, day: int, players: Iterable[int]) -> None:
        players = list(players)
        if len(players) == 1:
            self.log(f"player {players[0] + 1} is eliminated")
        else:
            elim_str = ", ".join(str(pid + 1) for pid in players)
            self.log(f"players {elim_str} are eliminated")

    # Low level I/O ----------------------------------------------------
    def log(self, message: str) -> None:
        if self.verbose:
            print(message)
        if self.file:
            self.file.write(message + "\n")
            self.file.flush()

    def close(self) -> None:
        if self.file:
            self.file.close()

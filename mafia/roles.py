"""Role enumeration and behaviour helpers.

The :class:`Game` engine interacts with players exclusively through these role
methods.  This keeps all role specific logic close to the role definition and
allows the engine to orchestrate phases without knowing which roles are
present.  Each method returns lightweight data structures that the engine
interprets generically.
"""

from __future__ import annotations

from enum import Enum, auto
from typing import Dict, Optional

from .actions import CheckResult, DonCheckResult

class Role(Enum):
    CIVILIAN = auto()
    MAFIA = auto()
    SHERIFF = auto()
    DON = auto()

    def is_mafia(self) -> bool:
        return self in {Role.MAFIA, Role.DON}

    def is_civilian(self) -> bool:
        return not self.is_mafia()

    # ------------------------------------------------------------------
    # Behavioural hooks -------------------------------------------------
    def perform_night_action(self, player: "Player", game: "Game") -> Dict[str, object]:
        """Execute this role's night action.

        Parameters
        ----------
        player:
            The :class:`~mafia.player.Player` performing the action.
        game:
            Current :class:`~mafia.game.Game` instance.  Strategies may inspect
            the game state to decide whom to target.

        Returns
        -------
        dict
            A mapping describing the performed action.  Common keys are
            ``kill``, ``kill_suggestion``, ``sheriff_check`` and ``don_check``.
            Unknown roles simply return an empty mapping.
        """

        actions: Dict[str, object] = {}
        alive_candidates = [p.pid for p in game.alive_players if p.pid != player.pid]

        if self == Role.SHERIFF:
            target = player.sheriff_check(game, alive_candidates)
            if target is not None:
                result = game.get_player(target).role.is_mafia()
                player.strategy.remember(target, result)  # type: ignore[attr-defined]
                actions["sheriff_check"] = CheckResult(
                    checker=player.pid, target=target, is_mafia=result
                )

        elif self == Role.DON:
            kill = player.mafia_kill(game, [p.pid for p in game.alive_players])
            if kill is not None:
                actions["kill"] = kill

            candidates = [pid for pid in alive_candidates if pid != kill]
            target = player.don_check(game, candidates)
            if target is not None:
                is_sheriff = game.get_player(target).role == Role.SHERIFF
                player.strategy.checked.add(target)  # type: ignore[attr-defined]
                if is_sheriff:
                    for mafia in game.alive_players:
                        if mafia.role.is_mafia():
                            mafia.strategy.known_sheriff = target  # type: ignore[attr-defined]
                actions["don_check"] = DonCheckResult(
                    checker=player.pid, target=target, is_sheriff=is_sheriff
                )

        elif self == Role.MAFIA:
            suggestion = player.mafia_kill(game, [p.pid for p in game.alive_players])
            if suggestion is not None:
                actions["kill_suggestion"] = suggestion

        # Civilians perform no night actions
        return actions

    def resolve_day_action(self, player: "Player", game: "Game", event: str) -> Optional[object]:
        """React to a day-phase ``event``.

        No built-in role currently reacts to day events, but the hook allows
        custom roles to implement behaviours such as automatic revelations or
        passive effects.
        """

        return None

    def delays_night_death(self) -> bool:
        """Return ``True`` if a night kill should be applied after all actions."""

        return self == Role.SHERIFF

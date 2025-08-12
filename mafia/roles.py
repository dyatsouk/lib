"""Role enumeration and behaviour helpers.

The :class:`~mafia.game.Game` engine interacts with players exclusively
through these role methods.  Keeping night logic with the role definition
removes the need for branchy ``if role == …`` checks inside the engine and
allows new roles to be added with minimal friction.
"""

from __future__ import annotations

from enum import Enum, auto
from typing import Dict, List

from .actions import CheckResult, DonCheckResult


class Role(Enum):
    """Enumeration of supported roles."""

    CIVILIAN = auto()
    MAFIA = auto()
    SHERIFF = auto()
    DON = auto()

    # ------------------------------------------------------------------
    # Role classification ------------------------------------------------
    def is_mafia(self) -> bool:
        """Return ``True`` for mafia and don roles."""

        return self in {Role.MAFIA, Role.DON}

    def is_civilian(self) -> bool:
        """Return ``True`` for civilian-aligned roles."""

        return not self.is_mafia()

    # ------------------------------------------------------------------
    # Behavioural hook ---------------------------------------------------
    def perform_night_action(self, player: "Player", game: "Game") -> Dict[str, object]:
        """Execute this role's night action.

        ``Game`` passes the list of **all** other players (alive or dead) to
        each role's handler so strategies can decide whether targeting
        eliminated players makes sense for them.
        """

        candidates = [p.pid for p in game.players if p.pid != player.pid]
        behaviour = _ROLE_BEHAVIOURS[self]
        return behaviour.night_action(player, game, candidates)

    def delays_night_death(self) -> bool:
        """Return ``True`` if a night kill is applied after all actions."""

        return self == Role.SHERIFF


# ---------------------------------------------------------------------------
# Behaviour classes ---------------------------------------------------------

class _BaseBehaviour:
    """Default role behaviour with no night action."""

    def night_action(self, player: "Player", game: "Game", candidates: List[int]) -> Dict[str, object]:
        return {}


class _SheriffBehaviour(_BaseBehaviour):
    """Sheriff checks a single candidate each night."""

    def night_action(self, player: "Player", game: "Game", candidates: List[int]) -> Dict[str, object]:
        target = player.sheriff_check(game, candidates)
        if target is None:
            return {}
        result = game.get_player(target).role.is_mafia()
        player.strategy.remember(target, result)  # type: ignore[attr-defined]
        return {
            "sheriff_check": CheckResult(
                checker=player.pid, target=target, is_mafia=result
            )
        }


class _DonBehaviour(_BaseBehaviour):
    """Don performs a mafia kill and then searches for the sheriff."""

    def night_action(self, player: "Player", game: "Game", candidates: List[int]) -> Dict[str, object]:
        actions: Dict[str, object] = {}
        kill = player.mafia_kill(game, candidates)
        if kill is not None:
            actions["kill"] = kill
        remaining = [pid for pid in candidates if pid != kill]
        target = player.don_check(game, remaining)
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
        return actions


class _MafiaBehaviour(_BaseBehaviour):
    """Regular mafia suggests a kill target."""

    def night_action(self, player: "Player", game: "Game", candidates: List[int]) -> Dict[str, object]:
        suggestion = player.mafia_kill(game, candidates)
        if suggestion is None:
            return {}
        return {"kill_suggestion": suggestion}


class _CivilianBehaviour(_BaseBehaviour):
    """Civilians have no night actions."""

    pass


_ROLE_BEHAVIOURS: Dict[Role, _BaseBehaviour] = {
    Role.SHERIFF: _SheriffBehaviour(),
    Role.DON: _DonBehaviour(),
    Role.MAFIA: _MafiaBehaviour(),
    Role.CIVILIAN: _CivilianBehaviour(),
}


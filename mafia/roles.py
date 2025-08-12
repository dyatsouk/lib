"""Role enumeration and behaviour helpers.

The :class:`Game` engine interacts with players exclusively through these role
methods.  This keeps all role specific logic close to the role definition and
allows the engine to orchestrate phases without knowing which roles are
present.  Each method returns lightweight data structures that the engine
interprets generically.
"""

from __future__ import annotations

from enum import Enum, auto
from typing import Callable, Dict, List, Optional

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
        """Execute this role's night action via a role-specific handler.

        All decision making resides in functions mapped in ``_NIGHT_ACTIONS``
        below.  This dispatch indirection keeps the enumeration free of bulky
        ``if/elif`` chains and allows new roles to plug in their behaviour
        without touching existing branches.
        """

        # Gather ids of other alive players so handlers work with plain lists
        candidates = [p.pid for p in game.alive_players if p.pid != player.pid]
        handler = _NIGHT_ACTIONS.get(self, _no_night_action)
        return handler(player, game, candidates)

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


# ---------------------------------------------------------------------------
# Night action handlers ------------------------------------------------------

def _sheriff_night_action(
    player: "Player", game: "Game", candidates: List[int]
) -> Dict[str, object]:
    """Have the sheriff check a candidate.

    The strategy may store the result for future reasoning via
    ``player.strategy.remember``.
    """

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


def _don_night_action(
    player: "Player", game: "Game", candidates: List[int]
) -> Dict[str, object]:
    """Resolve the don's kill and sheriff search.

    Information about a discovered sheriff is broadcast to other mafia
    strategies by setting ``known_sheriff`` on them.
    """

    actions: Dict[str, object] = {}
    kill = player.mafia_kill(game, [p.pid for p in game.alive_players])
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


def _mafia_night_action(
    player: "Player", game: "Game", candidates: List[int]
) -> Dict[str, object]:
    """Let a mafia member suggest a kill target."""

    suggestion = player.mafia_kill(game, [p.pid for p in game.alive_players])
    if suggestion is None:
        return {}
    return {"kill_suggestion": suggestion}


def _no_night_action(
    player: "Player", game: "Game", candidates: List[int]
) -> Dict[str, object]:
    """Default handler for roles without night actions."""

    return {}


NightAction = Callable[["Player", "Game", List[int]], Dict[str, object]]

# Mapping from Role to its dedicated night action function
_NIGHT_ACTIONS: Dict[Role, NightAction] = {
    Role.SHERIFF: _sheriff_night_action,
    Role.DON: _don_night_action,
    Role.MAFIA: _mafia_night_action,
    Role.CIVILIAN: _no_night_action,
}


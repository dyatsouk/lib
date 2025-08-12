"""Event dispatching utilities for the Mafia game engine.

The dispatcher implements a very small publish/subscribe mechanism.  The
:class:`~mafia.game.Game` engine emits structured events instead of calling a
logger directly.  Listeners can subscribe to the following events:

``speech_added``
    Emitted whenever a new :class:`~mafia.actions.SpeechLog` is recorded.
    Payload:
    ``day`` (int)
        Current day number starting from ``1``.
    ``index`` (int)
        Zero based index of the speech within the day.
    ``speech`` (:class:`~mafia.actions.SpeechLog`)
        The newly added speech entry.

``vote_cast``
    Fired when a player casts a vote during the day phase.
    Payload:
    ``day`` (int)
        Current day number.
    ``voter`` (int)
        Player id of the voter.
    ``target`` (int | None)
        Player id that received the vote or ``None`` for abstain.

``night_action``
    Covers all night time actions.  The ``action`` field specifies the
    particular event:

    ``mafia_kill``
        ``target`` (int | None) - player id targeted for the kill. ``success``
        (bool) indicates whether the kill succeeded.
    ``don_check``
        ``checker`` (int) - don player id, ``target`` (int) - checked player
        id, ``is_sheriff`` (bool) - whether the target was the sheriff.
    ``sheriff_check``
        ``checker`` (int) - sheriff player id, ``target`` (int) - checked
        player id, ``is_mafia`` (bool) - whether the target was mafia.

Other auxiliary events emitted by :class:`~mafia.game.Game` include
``day_started`` (payload ``day``), ``night_started`` (payload ``night``),
``players_eliminated`` (payload ``day`` and ``players`` list), ``no_elimination``
(payload ``day``) and ``info`` (payload ``message``) for generic strings.

The dispatcher is intentionally tiny; it merely stores a list of callbacks for
each event name and invokes them in the order they were registered.
"""

from __future__ import annotations

from collections import defaultdict
from typing import Any, Callable, DefaultDict, List


class EventDispatcher:
    """Lightweight synchronous event dispatcher.

    Handlers are registered via :meth:`subscribe` and receive keyword arguments
    specified by the emitter.  The dispatcher itself performs no error
    handling; exceptions raised by handlers will propagate to the caller.
    """

    def __init__(self) -> None:
        self._handlers: DefaultDict[str, List[Callable[..., None]]] = defaultdict(list)

    def subscribe(self, event: str, handler: Callable[..., None]) -> None:
        """Register ``handler`` to be invoked when ``event`` is emitted."""

        self._handlers[event].append(handler)

    def emit(self, event: str, **payload: Any) -> None:
        """Emit ``event`` with ``payload`` to all subscribed handlers."""

        for handler in self._handlers.get(event, []):
            handler(**payload)

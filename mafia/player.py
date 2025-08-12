"""Player model tying a role to a decision strategy.

The original implementation exposed only thin wrappers around the strategy
object.  For more complex simulations the :class:`~mafia.game.Game` engine now
interacts with players through a small behavioural interface.  This keeps role
specific logic close to the role itself and allows the engine to remain agnostic
of individual roles.
"""

from dataclasses import dataclass
from .roles import Role
from .strategies import BaseStrategy


@dataclass
class Player:
    """Representation of a single game participant.

    Parameters
    ----------
    pid:
        Unique identifier used throughout a game.
    role:
        The player's :class:`~mafia.roles.Role`.
    strategy:
        Strategy object providing decision methods.  Strategies are queried by
        the role methods to decide whom to nominate, vote for or target at
        night.
    alive:
        Flag indicating whether the player is still in the game.  It should not
        be modified directly; use :meth:`eliminate` instead so the change is
        explicit in the game flow.
    """

    pid: int
    role: Role
    strategy: BaseStrategy
    alive: bool = True

    def speak(self, game):
        return self.strategy.speak(self, game)

    def vote(self, game, nominations):
        return self.strategy.vote(self, game, nominations)

    def vote_elimination(self, game, candidates):
        """Decide whether all tied candidates should be eliminated.

        Parameters
        ----------
        game : Game
            Current game instance.
        candidates : list[int]
            Player ids who remain tied after a revote.

        Returns
        -------
        bool
            ``True`` if the player supports eliminating all tied candidates,
            ``False`` otherwise.
        """

        return self.strategy.vote_elimination(self, game, candidates)

    def sheriff_check(self, game, candidates):
        return self.strategy.sheriff_check(self, game, candidates)

    def mafia_kill(self, game, candidates):
        return self.strategy.mafia_kill(self, game, candidates)

    def don_check(self, game, candidates):
        return self.strategy.don_check(self, game, candidates)

    def last_words(self, game):
        return self.strategy.last_words(self, game)

    # ------------------------------------------------------------------
    # Behavioural helpers used by ``Game``.  These proxy to the role so the
    # engine never needs to perform ``if role == …`` checks.

    def perform_night_action(self, game):
        """Execute the player's night action and return any outcomes.

        The return value is a mapping whose interpretation is owned by the
        :class:`~mafia.game.Game` engine.  Typical keys include ``kill``,
        ``kill_suggestion``, ``sheriff_check`` and ``don_check``.
        """

        return self.role.perform_night_action(self, game)

    def eliminate(self) -> None:
        """Remove the player from the game.

        This is the canonical way to update ``alive`` so callers do not mutate
        the attribute directly.
        """

        self.alive = False

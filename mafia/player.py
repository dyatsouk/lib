from dataclasses import dataclass
from .roles import Role
from .strategies import BaseStrategy


@dataclass
class Player:
    """Representation of a single game participant.

    Each player has a unique ``pid``, an assigned :class:`Role` and a
    strategy object that decides their actions.  The ``alive`` flag tracks
    whether the player is still active in the game.
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

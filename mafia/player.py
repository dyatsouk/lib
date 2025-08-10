from dataclasses import dataclass
from .roles import Role
from .strategies import BaseStrategy


@dataclass
class Player:
    pid: int
    role: Role
    strategy: BaseStrategy
    alive: bool = True

    def speak(self, game):
        return self.strategy.speak(self, game)

    def vote(self, game, nominations):
        return self.strategy.vote(self, game, nominations)

    def sheriff_check(self, game, candidates):
        return self.strategy.sheriff_check(self, game, candidates)

    def mafia_kill(self, game, candidates):
        return self.strategy.mafia_kill(self, game, candidates)

    def don_check(self, game, candidates):
        return self.strategy.don_check(self, game, candidates)

    def last_words(self, game):
        return self.strategy.last_words(self, game)

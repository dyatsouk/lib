from enum import Enum, auto

class Role(Enum):
    CIVILIAN = auto()
    MAFIA = auto()
    SHERIFF = auto()
    DON = auto()

    def is_mafia(self) -> bool:
        return self in {Role.MAFIA, Role.DON}

    def is_civilian(self) -> bool:
        return not self.is_mafia()

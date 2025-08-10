from dataclasses import dataclass, field
from typing import Optional, List

@dataclass
class SheriffClaim:
    claimant: int
    target: int
    is_mafia: bool

@dataclass
class SpeechAction:
    nomination: Optional[int] = None
    claims: List[SheriffClaim] = field(default_factory=list)


@dataclass
class SpeechLog:
    """Record of a player's speech in order."""
    speaker: int
    action: SpeechAction

@dataclass
class Vote:
    voter: int
    target: Optional[int]

@dataclass
class CheckResult:
    checker: int
    target: int
    is_mafia: bool

@dataclass
class DonCheckResult:
    checker: int
    target: int
    is_sheriff: bool

@dataclass
class DayLog:
    speeches: List[SpeechLog]
    votes: List[Vote]
    eliminated: Optional[int]

@dataclass
class NightLog:
    sheriff_check: Optional[CheckResult]
    don_check: Optional[DonCheckResult]
    kill: Optional[int]

@dataclass
class RoundLog:
    day: DayLog
    night: Optional[NightLog]

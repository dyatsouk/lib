from dataclasses import dataclass
from typing import Optional

@dataclass
class SheriffClaim:
    claimant: int
    target: int
    is_mafia: bool

@dataclass
class SpeechAction:
    nomination: Optional[int] = None
    claim: Optional[SheriffClaim] = None

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
    speeches: dict  # pid -> SpeechAction
    votes: list  # List[Vote]
    eliminated: Optional[int]

@dataclass
class NightLog:
    sheriff_check: Optional[CheckResult]
    don_check: Optional[DonCheckResult]
    kill: Optional[int]

@dataclass
class RoundLog:
    day: DayLog
    night: NightLog

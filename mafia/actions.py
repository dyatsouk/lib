from dataclasses import dataclass, field
from typing import Optional, List

@dataclass
class SheriffClaim:
    """Statement by a sheriff about a player's alignment."""

    claimant: int
    target: int
    is_mafia: bool

@dataclass
class SpeechAction:
    """Actions a player may take during their speech."""

    nomination: Optional[int] = None
    claims: List[SheriffClaim] = field(default_factory=list)


@dataclass
class SpeechLog:
    """Record of a player's speech in order."""

    speaker: int
    action: SpeechAction

@dataclass
class Vote:
    """Record of a player's vote during the day."""

    voter: int
    # Target is ``None`` when no candidates were nominated. The game engine
    # ensures a valid target is always chosen if nominations exist.
    target: Optional[int]

@dataclass
class CheckResult:
    """Result of a sheriff's night-time investigation."""

    checker: int
    target: int
    is_mafia: bool

@dataclass
class DonCheckResult:
    """Outcome of the don's search for the sheriff."""

    checker: int
    target: int
    is_sheriff: bool

@dataclass
class DayLog:
    """Summary of a single day cycle."""

    speeches: List[SpeechLog]
    votes: List[Vote]
    eliminated: Optional[List[int]]

@dataclass
class NightLog:
    """Summary of a single night cycle."""

    sheriff_check: Optional[CheckResult]
    don_check: Optional[DonCheckResult]
    kill: Optional[int]

@dataclass
class RoundLog:
    """Combined record of one full round (day and optional night)."""

    day: DayLog
    night: Optional[NightLog]

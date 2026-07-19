from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass
class CommandResult:
    command: list[str]
    exit_code: int
    stdout: str
    stderr: str
    duration_ms: int
    timed_out: bool = False

    @property
    def passed(self) -> bool:
        return self.exit_code == 0 and not self.timed_out

    def to_dict(self) -> dict[str, Any]:
        return asdict(self) | {"passed": self.passed}


@dataclass
class CandidateResult:
    candidate_id: str
    strategy: str
    workspace: str
    commit_sha: str
    operation_count: int
    standard_test: CommandResult
    score: int
    challenge: CommandResult | None = None
    challenge_attempts: list[CommandResult] = field(default_factory=list)
    repair_commits: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["standard_test"] = self.standard_test.to_dict()
        data["challenge"] = self.challenge.to_dict() if self.challenge else None
        data["challenge_attempts"] = [attempt.to_dict() for attempt in self.challenge_attempts]
        return data

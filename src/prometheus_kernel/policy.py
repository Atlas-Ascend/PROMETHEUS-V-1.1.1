from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .engine_types import MissionPolicyError


@dataclass(frozen=True)
class ExecutionPolicy:
    allowed_executables: frozenset[str]
    command_timeout_seconds: int
    max_operations_per_candidate: int
    max_output_chars: int

    @classmethod
    def from_mission(cls, mission: dict[str, Any]) -> "ExecutionPolicy":
        raw = mission.get("policy", {})
        return cls(
            allowed_executables=frozenset(raw.get("allowed_executables", ["python"])),
            command_timeout_seconds=int(raw.get("command_timeout_seconds", 60)),
            max_operations_per_candidate=int(raw.get("max_operations_per_candidate", 100)),
            max_output_chars=int(raw.get("max_output_chars", 100_000)),
        )

    def validate(self, mission: dict[str, Any]) -> None:
        if not self.allowed_executables:
            raise MissionPolicyError("policy allowed_executables cannot be empty")
        if not 1 <= self.command_timeout_seconds <= 3600:
            raise MissionPolicyError("command_timeout_seconds must be between 1 and 3600")
        for field in ("standard_test", "challenge_test"):
            command = mission[field]
            if not isinstance(command, list) or not command or not all(isinstance(part, str) for part in command):
                raise MissionPolicyError(f"{field} must be a non-empty string array")
            if command[0] not in self.allowed_executables:
                raise MissionPolicyError(f"{field} executable is not allowed: {command[0]}")
        for candidate in mission["candidates"]:
            for field in ("operations", "repair_operations"):
                count = len(candidate.get(field, []))
                if count > self.max_operations_per_candidate:
                    raise MissionPolicyError(
                        f"candidate {candidate['id']} exceeds operation limit in {field}: {count}"
                    )

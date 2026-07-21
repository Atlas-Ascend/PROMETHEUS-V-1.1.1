from __future__ import annotations

import json
import os
import shutil
import subprocess
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Callable


class CodexProviderError(RuntimeError):
    pass


SENSITIVE_ENVIRONMENT_KEYS = {
    "DISCORD_BOT_TOKEN",
    "DISCORD_APPLICATION_ID",
    "DISCORD_GUILD_ID",
    "GITHUB_TOKEN",
    "GH_TOKEN",
    "OPENAI_API_KEY",
    "CODEX_API_KEY",
}


@dataclass
class CodexExecution:
    candidate_id: str
    command: list[str]
    exit_code: int
    duration_ms: int
    transcript: str
    stderr: str
    final_message: str

    @property
    def passed(self) -> bool:
        return self.exit_code == 0

    def to_dict(self) -> dict[str, Any]:
        return asdict(self) | {"passed": self.passed}


def scrubbed_environment(source: dict[str, str] | None = None) -> dict[str, str]:
    environment = dict(source or os.environ)
    for key in SENSITIVE_ENVIRONMENT_KEYS:
        environment.pop(key, None)
    return environment


def build_candidate_prompt(mission: dict[str, Any], candidate: dict[str, Any]) -> str:
    acceptance = "\n".join(
        f"- {criterion}" for criterion in mission.get("acceptance_criteria", [])
    ) or "- Preserve the stated objective and leave the repository testable."
    constraints = "\n".join(
        f"- {constraint}" for constraint in mission.get("constraints", [])
    ) or "- Work only inside the current repository worktree."
    standard_test = " ".join(mission["standard_test"])
    challenge_test = " ".join(mission["challenge_test"])
    return f"""You are one isolated PROMETHEUS candidate implementation lane.

Mission: {mission['mission_id']}
Objective: {mission['objective']}
Candidate: {candidate['id']}
Strategy: {candidate['strategy']}

Candidate-specific direction:
{candidate.get('prompt', 'Implement the objective using the named strategy.')}

Acceptance criteria:
{acceptance}

Constraints:
{constraints}

Required verification commands:
- Standard: {standard_test}
- Adversarial: {challenge_test}

Operate directly in the current worktree. Inspect the repository before editing.
Implement a complete, coherent patch for this strategy. Add or update focused tests
and documentation where the behavior changes. Run relevant checks before finishing.
Do not push, open a pull request, modify Git remotes, expose credentials, or edit
outside the worktree. Do not merely describe a solution: leave the implementation
in the worktree and finish with a concise summary of changes, tests, and remaining risks.
"""


def build_challenge_prompt(
    mission: dict[str, Any], candidate: dict[str, Any], candidate_summary: dict[str, Any]
) -> str:
    criteria = "\n".join(
        f"- {criterion}" for criterion in mission.get("acceptance_criteria", [])
    )
    return f"""Act as the independent PROMETHEUS Adversarial Twin for the promoted leader.

Mission: {mission['mission_id']}
Objective: {mission['objective']}
Leader: {candidate['id']} — {candidate['strategy']}
Observed changed files: {', '.join(candidate_summary.get('changed_files', []))}

Acceptance criteria:
{criteria}

Inspect the actual diff and repository. Look for correctness failures, incomplete
requirements, unsafe path or process handling, secret leakage, brittle tests,
non-idempotent behavior, unverifiable claims, and Windows/Linux incompatibilities.
Repair every material finding you can prove. Add regression tests for repaired faults.
Run the standard and adversarial commands. Do not push or open a pull request.
Leave all verified repairs in the worktree and finish with findings, repairs, tests,
and any unresolved risk.
"""


class CodexProvider:
    """Non-interactive Codex CLI adapter for an isolated candidate worktree."""

    def __init__(
        self,
        executable: str = "codex",
        model: str | None = None,
        sandbox: str = "workspace-write",
        timeout_seconds: int = 3600,
    ):
        self.executable = executable
        self.model = model
        self.sandbox = sandbox
        self.timeout_seconds = timeout_seconds

    def preflight(self) -> dict[str, str]:
        resolved = shutil.which(self.executable)
        if not resolved:
            raise CodexProviderError(
                f"Codex CLI was not found: {self.executable}. Install/login before the campaign."
            )
        return {"executable": resolved, "sandbox": self.sandbox, "model": self.model or "default"}

    def command(self, final_message: Path, prompt: str) -> list[str]:
        command = [
            self.executable,
            "exec",
            "--sandbox",
            self.sandbox,
            "--ephemeral",
            "--json",
            "--output-last-message",
            str(final_message),
        ]
        if self.model:
            command.extend(["--model", self.model])
        command.append(prompt)
        return command

    def run(
        self,
        workspace: Path,
        candidate_id: str,
        prompt: str,
        evidence_dir: Path,
        event_callback: Callable[[dict[str, Any]], None] | None = None,
    ) -> CodexExecution:
        evidence_dir.mkdir(parents=True, exist_ok=True)
        transcript_path = evidence_dir / f"{candidate_id}-codex.jsonl"
        stderr_path = evidence_dir / f"{candidate_id}-codex.stderr.log"
        final_path = evidence_dir / f"{candidate_id}-final.md"
        command = self.command(final_path, prompt)
        started = time.monotonic()
        environment = scrubbed_environment()
        try:
            process = subprocess.Popen(
                command,
                cwd=workspace,
                env=environment,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            try:
                stdout, stderr = process.communicate(timeout=self.timeout_seconds)
            except subprocess.TimeoutExpired:
                process.kill()
                stdout, stderr = process.communicate()
                stderr += f"\nCodex timed out after {self.timeout_seconds} seconds."
                exit_code = 124
            else:
                exit_code = process.returncode
        except OSError as error:
            raise CodexProviderError(f"Codex execution could not start: {error}") from error

        transcript_path.write_text(stdout, encoding="utf-8")
        stderr_path.write_text(stderr, encoding="utf-8")
        final_message = final_path.read_text(encoding="utf-8") if final_path.is_file() else ""
        execution = CodexExecution(
            candidate_id=candidate_id,
            command=[part if part != prompt else "<PROMPT>" for part in command],
            exit_code=exit_code,
            duration_ms=round((time.monotonic() - started) * 1000),
            transcript=str(transcript_path),
            stderr=str(stderr_path),
            final_message=str(final_path),
        )
        if event_callback:
            event_callback(
                {
                    "type": "codex.completed" if execution.passed else "codex.failed",
                    "candidate_id": candidate_id,
                    "exit_code": exit_code,
                    "duration_ms": execution.duration_ms,
                }
            )
        if not execution.passed:
            tail = stderr[-4000:]
            raise CodexProviderError(
                f"Codex candidate {candidate_id} failed with exit code {exit_code}:\n{tail}"
            )
        return execution

    def generate(
        self,
        workspace: Path,
        mission: dict[str, Any],
        candidate: dict[str, Any],
        evidence_dir: Path,
        event_callback: Callable[[dict[str, Any]], None] | None = None,
    ) -> CodexExecution:
        return self.run(
            workspace,
            candidate["id"],
            build_candidate_prompt(mission, candidate),
            evidence_dir,
            event_callback,
        )

    def challenge(
        self,
        workspace: Path,
        mission: dict[str, Any],
        candidate: dict[str, Any],
        candidate_summary: dict[str, Any],
        evidence_dir: Path,
        event_callback: Callable[[dict[str, Any]], None] | None = None,
    ) -> CodexExecution:
        return self.run(
            workspace,
            f"{candidate['id']}-adversarial",
            build_challenge_prompt(mission, candidate, candidate_summary),
            evidence_dir,
            event_callback,
        )


def transcript_event_types(path: Path) -> list[str]:
    types: list[str] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(event.get("type"), str):
            types.append(event["type"])
    return types

from __future__ import annotations

import json
import platform
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .models import CandidateResult
from .ledger import EventLedger, verify_ledger
from .operations import apply_operations
from .policy import ExecutionPolicy
from .util import (
    artifact_manifest,
    canonical_json,
    require_success,
    run_command,
    sha256_file,
    sha256_text,
)


class MissionError(RuntimeError):
    pass


def load_mission(path: Path) -> dict[str, Any]:
    mission = json.loads(path.read_text(encoding="utf-8"))
    required = {"mission_id", "objective", "seed_path", "candidates", "standard_test", "challenge_test"}
    missing = sorted(required - mission.keys())
    if missing:
        raise MissionError(f"mission missing required fields: {', '.join(missing)}")
    if len(mission["candidates"]) < 3:
        raise MissionError("P0 requires at least three candidate strategies")
    ids = [candidate["id"] for candidate in mission["candidates"]]
    if len(ids) != len(set(ids)):
        raise MissionError("candidate IDs must be unique")
    ExecutionPolicy.from_mission(mission).validate(mission)
    return mission


def _git(cwd: Path, *args: str):
    result = run_command(["git", *args], cwd)
    require_success(result, f"git {' '.join(args)}")
    return result


def _commit(workspace: Path, message: str) -> str:
    _git(workspace, "add", "-A")
    _git(workspace, "commit", "--allow-empty", "-m", message)
    return _git(workspace, "rev-parse", "HEAD").stdout.strip()


def _prepare_base(seed: Path, base_repo: Path) -> str:
    shutil.copytree(seed, base_repo)
    _git(base_repo, "init", "-b", "main")
    _git(base_repo, "config", "user.name", "PROMETHEUS")
    _git(base_repo, "config", "user.email", "prometheus@local.invalid")
    return _commit(base_repo, "seed mission workspace")


def _create_worktree(base_repo: Path, worktree: Path, candidate_id: str) -> None:
    branch = f"candidate/{candidate_id}"
    _git(base_repo, "branch", branch)
    _git(base_repo, "worktree", "add", str(worktree), branch)
    _git(worktree, "config", "user.name", "PROMETHEUS")
    _git(worktree, "config", "user.email", "prometheus@local.invalid")


def _score(passed: bool, operation_count: int) -> int:
    return (1000 if passed else 0) - operation_count


def execute_mission(mission_path: Path, output_root: Path | None = None) -> dict[str, Any]:
    mission_path = mission_path.resolve()
    mission = load_mission(mission_path)
    policy = ExecutionPolicy.from_mission(mission)
    project_root = mission_path.parent.parent
    seed = (project_root / mission["seed_path"]).resolve()
    if not seed.is_dir():
        raise MissionError(f"seed_path is not a directory: {seed}")

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    run_id = f"{mission['mission_id']}-{timestamp}"
    root = (output_root or project_root / ".prometheus" / "runs") / run_id
    root.mkdir(parents=True, exist_ok=False)
    mission_snapshot = root / "mission.json"
    shutil.copy2(mission_path, mission_snapshot)
    ledger = EventLedger(root / "events.jsonl")
    ledger.append(
        "mission.accepted",
        {"mission_id": mission["mission_id"], "mission_sha256": sha256_file(mission_snapshot)},
    )
    base_repo = root / "base-repository"
    seed_commit = _prepare_base(seed, base_repo)
    ledger.append("seed.captured", {"seed_commit": seed_commit, "seed_path": mission["seed_path"]})

    candidates: list[CandidateResult] = []
    definitions: dict[str, dict[str, Any]] = {}
    for definition in mission["candidates"]:
        candidate_id = definition["id"]
        definitions[candidate_id] = definition
        workspace = root / "worktrees" / candidate_id
        workspace.parent.mkdir(parents=True, exist_ok=True)
        _create_worktree(base_repo, workspace, candidate_id)
        operations = definition.get("operations", [])
        apply_operations(workspace, operations)
        commit_sha = _commit(workspace, f"candidate: {candidate_id}")
        ledger.append(
            "candidate.created",
            {"candidate_id": candidate_id, "commit_sha": commit_sha, "operation_count": len(operations)},
        )
        standard = run_command(
            mission["standard_test"],
            workspace,
            timeout_seconds=policy.command_timeout_seconds,
            max_output_chars=policy.max_output_chars,
        )
        ledger.append("candidate.standard_tested", {"candidate_id": candidate_id, "result": standard.to_dict()})
        candidates.append(
            CandidateResult(
                candidate_id=candidate_id,
                strategy=definition.get("strategy", candidate_id),
                workspace=workspace.relative_to(root).as_posix(),
                commit_sha=commit_sha,
                operation_count=len(operations),
                standard_test=standard,
                score=_score(standard.passed, len(operations)),
            )
        )

    viable = [candidate for candidate in candidates if candidate.standard_test.passed]
    if not viable:
        raise MissionError("no candidate passed the standard test gate")
    leader = sorted(viable, key=lambda item: (-item.score, item.candidate_id))[0]
    ledger.append("leader.selected", {"candidate_id": leader.candidate_id, "score": leader.score})
    leader_workspace = root / leader.workspace
    leader.challenge = run_command(
        mission["challenge_test"],
        leader_workspace,
        timeout_seconds=policy.command_timeout_seconds,
        max_output_chars=policy.max_output_chars,
    )
    leader.challenge_attempts.append(leader.challenge)
    ledger.append(
        "leader.challenged",
        {"candidate_id": leader.candidate_id, "attempt": 1, "result": leader.challenge.to_dict()},
    )

    repairs_applied = False
    if not leader.challenge.passed:
        repairs = definitions[leader.candidate_id].get("repair_operations", [])
        if not repairs:
            raise MissionError(f"leader {leader.candidate_id} failed challenge with no repair plan")
        apply_operations(leader_workspace, repairs)
        leader.repair_commits.append(_commit(leader_workspace, f"repair: {leader.candidate_id}"))
        ledger.append(
            "leader.repaired",
            {"candidate_id": leader.candidate_id, "commit_sha": leader.repair_commits[-1]},
        )
        repairs_applied = True
        leader.standard_test = run_command(
            mission["standard_test"],
            leader_workspace,
            timeout_seconds=policy.command_timeout_seconds,
            max_output_chars=policy.max_output_chars,
        )
        ledger.append(
            "leader.standard_retested",
            {"candidate_id": leader.candidate_id, "result": leader.standard_test.to_dict()},
        )
        leader.challenge = run_command(
            mission["challenge_test"],
            leader_workspace,
            timeout_seconds=policy.command_timeout_seconds,
            max_output_chars=policy.max_output_chars,
        )
        leader.challenge_attempts.append(leader.challenge)
        ledger.append(
            "leader.challenged",
            {"candidate_id": leader.candidate_id, "attempt": 2, "result": leader.challenge.to_dict()},
        )

    if not leader.standard_test.passed or not leader.challenge.passed:
        raise MissionError(f"leader {leader.candidate_id} failed post-repair promotion gates")

    promoted = root / "promoted"
    shutil.copytree(leader_workspace, promoted, ignore=shutil.ignore_patterns(".git"))
    artifacts = artifact_manifest(promoted)
    promoted_commit = _git(leader_workspace, "rev-parse", "HEAD").stdout.strip()
    ledger.append(
        "candidate.promoted",
        {"candidate_id": leader.candidate_id, "commit_sha": promoted_commit, "artifact_count": len(artifacts)},
    )
    payload = {
        "schema": "prometheus.receipt.v1",
        "run_id": run_id,
        "mission_id": mission["mission_id"],
        "objective": mission["objective"],
        "mission_sha256": sha256_file(mission_snapshot),
        "created_at": datetime.now(timezone.utc).isoformat(),
        "seed_commit": seed_commit,
        "candidate_results": [candidate.to_dict() for candidate in candidates],
        "leader": leader.candidate_id,
        "repairs_applied": repairs_applied,
        "promoted_commit": promoted_commit,
        "artifacts": artifacts,
        "event_ledger": {
            "path": "events.jsonl",
            "events": ledger.index,
            "chain_head": ledger.head,
            "sha256": sha256_file(ledger.path),
        },
        "execution_policy": {
            "allowed_executables": sorted(policy.allowed_executables),
            "command_timeout_seconds": policy.command_timeout_seconds,
            "max_operations_per_candidate": policy.max_operations_per_candidate,
            "max_output_chars": policy.max_output_chars,
        },
        "runtime": {
            "python": sys.version.split()[0],
            "platform": platform.platform(),
        },
    }
    receipt = payload | {"receipt_hash": sha256_text(canonical_json(payload))}
    receipt_path = root / "promotion-receipt.json"
    receipt_path.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    genome = {
        "schema": "prometheus.capability-genome.v1",
        "mission_id": mission["mission_id"],
        "run_id": run_id,
        "promoted_candidate": leader.candidate_id,
        "capabilities": [
            "isolated-git-worktree-generation",
            "deterministic-candidate-operations",
            "local-test-execution",
            "adversarial-challenge",
            "repair-before-promotion",
            "hash-verifiable-receipt",
        ],
        "evidence_receipt_hash": receipt["receipt_hash"],
    }
    genome_path = root / "capability-genome.json"
    genome_path.write_text(json.dumps(genome, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    summary = {
        "run_id": run_id,
        "status": "PROMOTED",
        "leader": leader.candidate_id,
        "repairs_applied": repairs_applied,
        "receipt": str(receipt_path),
        "receipt_hash": receipt["receipt_hash"],
        "capability_genome": str(genome_path),
        "promoted_workspace": str(promoted),
    }
    (root / "summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return summary


def verify_receipt(path: Path) -> bool:
    receipt = json.loads(path.read_text(encoding="utf-8"))
    expected = receipt.pop("receipt_hash")
    if expected != sha256_text(canonical_json(receipt)):
        return False
    ledger_info = receipt.get("event_ledger", {})
    ledger_path = path.parent / ledger_info.get("path", "")
    if not ledger_path.is_file() or sha256_file(ledger_path) != ledger_info.get("sha256"):
        return False
    lines = ledger_path.read_text(encoding="utf-8").splitlines()
    if len(lines) != ledger_info.get("events") or not verify_ledger(ledger_path):
        return False
    if json.loads(lines[-1]).get("event_hash") != ledger_info.get("chain_head"):
        return False
    promoted = path.parent / "promoted"
    for artifact in receipt.get("artifacts", []):
        artifact_path = (promoted / artifact["path"]).resolve()
        if promoted.resolve() not in artifact_path.parents or not artifact_path.is_file():
            return False
        if sha256_file(artifact_path) != artifact["sha256"] or artifact_path.stat().st_size != artifact["bytes"]:
            return False
    return True

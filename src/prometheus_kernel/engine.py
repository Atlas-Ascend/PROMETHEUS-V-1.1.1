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


def _write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _write_packet(root: Path, packet_id: str, packet_type: str, payload: dict[str, Any]) -> dict[str, Any]:
    packet = {
        "schema": "prometheus.packet.v1",
        "packet_id": packet_id,
        "packet_type": packet_type,
        "payload": payload,
    }
    path = root / "packets" / f"{packet_id}.json"
    _write_json(path, packet)
    return {"packet_id": packet_id, "packet_type": packet_type, "path": path.relative_to(root).as_posix(), "sha256": sha256_file(path)}


def _capture_execution(root: Path, phase: str, candidate_id: str, result: Any) -> dict[str, Any]:
    evidence_root = root / "evidence" / candidate_id / phase
    evidence_root.mkdir(parents=True, exist_ok=True)
    stdout_path = evidence_root / "stdout.log"
    stderr_path = evidence_root / "stderr.log"
    stdout_path.write_text(result.stdout, encoding="utf-8")
    stderr_path.write_text(result.stderr, encoding="utf-8")
    record = result.to_dict() | {
        "stdout_path": stdout_path.relative_to(root).as_posix(),
        "stdout_sha256": sha256_file(stdout_path),
        "stderr_path": stderr_path.relative_to(root).as_posix(),
        "stderr_sha256": sha256_file(stderr_path),
    }
    record_path = evidence_root / "execution.json"
    _write_json(record_path, record)
    return {
        "candidate_id": candidate_id,
        "phase": phase,
        "path": record_path.relative_to(root).as_posix(),
        "sha256": sha256_file(record_path),
        "stdout_path": record["stdout_path"],
        "stdout_sha256": record["stdout_sha256"],
        "stderr_path": record["stderr_path"],
        "stderr_sha256": record["stderr_sha256"],
    }


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
    root = ((output_root or project_root / ".prometheus" / "runs") / run_id).resolve()
    root.mkdir(parents=True, exist_ok=False)
    mission_snapshot = root / "mission.json"
    shutil.copy2(mission_path, mission_snapshot)
    ledger = EventLedger(root / "events.jsonl")
    packets: list[dict[str, Any]] = []
    execution_evidence: list[dict[str, Any]] = []
    packets.append(_write_packet(root, "PKT-000-MISSION", "MISSION", {
        "mission_id": mission["mission_id"],
        "objective": mission["objective"],
        "mission_sha256": sha256_file(mission_snapshot),
    }))
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
        packets.append(_write_packet(root, f"PKT-CANDIDATE-{candidate_id}", "CANDIDATE_STRATEGY", {
            "mission_id": mission["mission_id"],
            "candidate_id": candidate_id,
            "strategy": definition.get("strategy", candidate_id),
            "operations": operations,
            "repair_operations": definition.get("repair_operations", []),
        }))
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
        execution_evidence.append(_capture_execution(root, "standard-initial", candidate_id, standard))
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
    arbitration = {
        "leader": leader.candidate_id,
        "ranking": [
            {
                "candidate_id": candidate.candidate_id,
                "score": candidate.score,
                "standard_passed": candidate.standard_test.passed,
                "decision": "PROVISIONAL_LEADER" if candidate.candidate_id == leader.candidate_id else "REJECTED",
                "reason": "highest measured score" if candidate.candidate_id == leader.candidate_id else "lower measured score or failed standard gate",
            }
            for candidate in sorted(candidates, key=lambda item: (-item.score, item.candidate_id))
        ],
    }
    arbitration_path = root / "evidence" / "arbitration.json"
    _write_json(arbitration_path, arbitration)
    packets.append(_write_packet(root, "PKT-ARBITRATION", "ARBITRATION", arbitration))
    ledger.append("leader.selected", {"candidate_id": leader.candidate_id, "score": leader.score})
    leader_workspace = root / leader.workspace
    leader.challenge = run_command(
        mission["challenge_test"],
        leader_workspace,
        timeout_seconds=policy.command_timeout_seconds,
        max_output_chars=policy.max_output_chars,
    )
    leader.challenge_attempts.append(leader.challenge)
    execution_evidence.append(_capture_execution(root, "challenge-initial", leader.candidate_id, leader.challenge))
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
        execution_evidence.append(_capture_execution(root, "standard-retest", leader.candidate_id, leader.standard_test))
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
        execution_evidence.append(_capture_execution(root, "challenge-retest", leader.candidate_id, leader.challenge))
        ledger.append(
            "leader.challenged",
            {"candidate_id": leader.candidate_id, "attempt": 2, "result": leader.challenge.to_dict()},
        )

    if not leader.standard_test.passed or not leader.challenge.passed:
        raise MissionError(f"leader {leader.candidate_id} failed post-repair promotion gates")

    packets.append(_write_packet(root, "PKT-PROMOTION", "PROMOTION_DECISION", {
        "candidate_id": leader.candidate_id,
        "repairs_applied": repairs_applied,
        "standard_passed": leader.standard_test.passed,
        "challenge_passed": leader.challenge.passed,
        "decision": "PROMOTE",
    }))

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
        "packets": packets,
        "execution_evidence": execution_evidence,
        "arbitration": {
            "path": arbitration_path.relative_to(root).as_posix(),
            "sha256": sha256_file(arbitration_path),
        },
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
            "typed-command-to-proof-packets",
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

    build_truth = {
        "schema": "prometheus.build-truth.v1",
        "run_id": run_id,
        "mission_id": mission["mission_id"],
        "state": "PROVEN",
        "proven_claims": [
            "mission-interpreted",
            "packets-generated",
            "three-distinct-candidates",
            "git-worktree-isolation",
            "real-subprocess-execution",
            "hashed-execution-evidence",
            "measured-arbitration",
            "adversarial-challenge",
            "repair-and-retest",
            "promotion-receipt",
            "capability-genome",
        ],
        "receipt": "promotion-receipt.json",
        "receipt_hash": receipt["receipt_hash"],
        "capability_genome": "capability-genome.json",
        "external_claims": {"discord_live_deployment": "NOT_CLAIMED"},
    }
    build_truth_path = root / "build-truth.json"
    _write_json(build_truth_path, build_truth)

    summary = {
        "run_id": run_id,
        "status": "PROMOTED",
        "leader": leader.candidate_id,
        "repairs_applied": repairs_applied,
        "receipt": str(receipt_path),
        "receipt_hash": receipt["receipt_hash"],
        "capability_genome": str(genome_path),
        "build_truth": str(build_truth_path),
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
    for record in receipt.get("packets", []) + receipt.get("execution_evidence", []):
        evidence_path = (path.parent / record.get("path", "")).resolve()
        if path.parent.resolve() not in evidence_path.parents or not evidence_path.is_file():
            return False
        if sha256_file(evidence_path) != record.get("sha256"):
            return False
        for stream in ("stdout", "stderr"):
            stream_path_value = record.get(f"{stream}_path")
            if stream_path_value is None:
                continue
            stream_path = (path.parent / stream_path_value).resolve()
            if path.parent.resolve() not in stream_path.parents or not stream_path.is_file():
                return False
            if sha256_file(stream_path) != record.get(f"{stream}_sha256"):
                return False
    arbitration = receipt.get("arbitration", {})
    arbitration_path = (path.parent / arbitration.get("path", "")).resolve()
    if path.parent.resolve() not in arbitration_path.parents or not arbitration_path.is_file():
        return False
    if sha256_file(arbitration_path) != arbitration.get("sha256"):
        return False
    promoted = path.parent / "promoted"
    for artifact in receipt.get("artifacts", []):
        artifact_path = (promoted / artifact["path"]).resolve()
        if promoted.resolve() not in artifact_path.parents or not artifact_path.is_file():
            return False
        if sha256_file(artifact_path) != artifact["sha256"] or artifact_path.stat().st_size != artifact["bytes"]:
            return False
    return True

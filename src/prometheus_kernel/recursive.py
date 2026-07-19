from __future__ import annotations

import json
import re
import shutil
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .case_study import CaseStudyPublisher
from .codex_provider import CodexProvider
from .ledger import EventLedger, verify_ledger
from .util import canonical_json, require_success, run_command, sha256_file, sha256_text


class RecursiveCampaignError(RuntimeError):
    pass


def load_recursive_mission(path: Path) -> dict[str, Any]:
    mission = json.loads(path.read_text(encoding="utf-8"))
    required = {
        "schema",
        "mission_id",
        "objective",
        "source_repo",
        "standard_test",
        "challenge_test",
        "candidates",
        "promotion",
    }
    missing = sorted(required - mission.keys())
    if missing:
        raise RecursiveCampaignError(f"recursive mission missing fields: {missing}")
    if mission["schema"] != "prometheus.recursive-mission.v1":
        raise RecursiveCampaignError(f"unsupported recursive mission schema: {mission['schema']}")
    if len(mission["candidates"]) < 3:
        raise RecursiveCampaignError("recursive campaigns require at least three candidates")
    candidate_ids = [candidate["id"] for candidate in mission["candidates"]]
    if len(candidate_ids) != len(set(candidate_ids)):
        raise RecursiveCampaignError("recursive candidate IDs must be unique")
    for field in ("standard_test", "challenge_test"):
        command = mission[field]
        if not isinstance(command, list) or not command or not all(isinstance(part, str) for part in command):
            raise RecursiveCampaignError(f"{field} must be a non-empty string array")
    return mission


def _git(cwd: Path, *args: str):
    result = run_command(["git", *args], cwd, timeout_seconds=300)
    require_success(result, f"git {' '.join(args)}")
    return result


def _slug(value: str) -> str:
    return re.sub(r"[^a-z0-9-]+", "-", value.lower()).strip("-")


def _changed_files(workspace: Path) -> list[str]:
    result = _git(workspace, "status", "--porcelain=v1", "--untracked-files=all")
    files: list[str] = []
    for line in result.stdout.splitlines():
        path = line[3:]
        if " -> " in path:
            path = path.split(" -> ", 1)[1]
        files.append(path)
    return sorted(set(files))


def _commit(workspace: Path, message: str) -> str:
    _git(workspace, "config", "user.name", "PROMETHEUS Recursive Forge")
    _git(workspace, "config", "user.email", "prometheus@local.invalid")
    _git(workspace, "add", "-A")
    _git(workspace, "commit", "-m", message)
    return _git(workspace, "rev-parse", "HEAD").stdout.strip()


def _run_gate(command: list[str], workspace: Path, mission: dict[str, Any]):
    policy = mission.get("policy", {})
    executable = command[0]
    allowed = set(policy.get("allowed_executables", ["python"]))
    if executable not in allowed:
        raise RecursiveCampaignError(f"gate executable is not allowed: {executable}")
    return run_command(
        command,
        workspace,
        env={"PYTHONPATH": str(workspace / "src")},
        timeout_seconds=int(policy.get("command_timeout_seconds", 900)),
        max_output_chars=int(policy.get("max_output_chars", 100_000)),
    )


def _source_manifest(workspace: Path) -> list[dict[str, Any]]:
    artifacts: list[dict[str, Any]] = []
    root = workspace.resolve()
    for path in sorted(root.rglob("*")):
        if not path.is_file():
            continue
        relative = path.relative_to(root)
        if ".git" in relative.parts or ".prometheus" in relative.parts:
            continue
        if len(relative.parts) >= 2 and relative.parts[:2] == ("proof", "recursive"):
            continue
        artifacts.append(
            {
                "path": relative.as_posix(),
                "sha256": sha256_file(path),
                "bytes": path.stat().st_size,
            }
        )
    return artifacts


def _portable_candidate(result: dict[str, Any]) -> dict[str, Any]:
    portable = json.loads(json.dumps(result, default=str))
    candidate_id = portable.get("candidate_id", "unknown")
    if "workspace" in portable:
        portable["workspace"] = f"worktrees/{candidate_id}"
    codex = portable.get("codex")
    if isinstance(codex, dict):
        for field in ("transcript", "stderr", "final_message"):
            if codex.get(field):
                codex[field] = f"codex/{Path(codex[field]).name}"
    return portable


def _candidate_worker(
    source_repo: Path,
    root: Path,
    run_id: str,
    mission: dict[str, Any],
    candidate: dict[str, Any],
    provider: CodexProvider,
    publisher: CaseStudyPublisher,
) -> dict[str, Any]:
    candidate_id = candidate["id"]
    workspace = root / "worktrees" / candidate_id
    branch = f"prometheus/candidate/{_slug(run_id)}/{_slug(candidate_id)}"
    publisher.publish({"type": "candidate.started", "candidate_id": candidate_id, "strategy": candidate["strategy"]})
    try:
        generation = provider.generate(
            workspace,
            mission,
            candidate,
            root / "codex",
            publisher.publish,
        )
        changed_files = _changed_files(workspace)
        if not changed_files:
            raise RecursiveCampaignError(f"candidate {candidate_id} produced no repository changes")
        limit = int(mission.get("policy", {}).get("max_changed_files", 200))
        if len(changed_files) > limit:
            raise RecursiveCampaignError(
                f"candidate {candidate_id} changed {len(changed_files)} files; limit is {limit}"
            )
        commit = _commit(workspace, f"candidate({candidate_id}): {mission['objective']}")
        standard = _run_gate(mission["standard_test"], workspace, mission)
        result = {
            "candidate_id": candidate_id,
            "strategy": candidate["strategy"],
            "branch": branch,
            "workspace": str(workspace),
            "commit": commit,
            "changed_files": changed_files,
            "codex": generation.to_dict(),
            "standard_test": standard.to_dict(),
            "score": (100_000 if standard.passed else 0) - len(changed_files),
            "passed": standard.passed,
        }
        publisher.publish(
            {
                "type": "candidate.completed",
                "candidate_id": candidate_id,
                "passed": standard.passed,
                "commit": commit[:12],
                "changed_files": len(changed_files),
            }
        )
        return result
    except Exception as error:
        publisher.publish({"type": "candidate.failed", "candidate_id": candidate_id, "error": str(error)[:900]})
        return {
            "candidate_id": candidate_id,
            "strategy": candidate["strategy"],
            "branch": branch,
            "workspace": str(workspace),
            "passed": False,
            "score": -1,
            "error": str(error),
        }


def _open_draft_pr(
    workspace: Path,
    repository: str,
    branch: str,
    base: str,
    title: str,
    body_path: Path,
) -> str:
    if not shutil.which("gh"):
        raise RecursiveCampaignError("GitHub CLI 'gh' is required to open the draft PR")
    result = run_command(
        [
            "gh",
            "pr",
            "create",
            "--repo",
            repository,
            "--base",
            base,
            "--head",
            branch,
            "--draft",
            "--title",
            title,
            "--body-file",
            str(body_path),
        ],
        workspace,
        timeout_seconds=180,
    )
    require_success(result, "gh pr create")
    return result.stdout.strip().splitlines()[-1]


def run_recursive_campaign(
    mission_path: Path,
    output_root: Path | None = None,
    provider: CodexProvider | None = None,
    publisher: CaseStudyPublisher | None = None,
    confirm_repo: str | None = None,
    push: bool = False,
    open_pr: bool = False,
) -> dict[str, Any]:
    mission_path = mission_path.resolve()
    mission = load_recursive_mission(mission_path)
    project_root = mission_path.parent.parent
    source_repo = (project_root / mission["source_repo"]).resolve()
    if not (source_repo / ".git").exists():
        raise RecursiveCampaignError(f"source_repo is not a Git worktree: {source_repo}")
    if _git(source_repo, "status", "--porcelain").stdout.strip():
        raise RecursiveCampaignError("source repository must be clean before recursive execution")

    promotion = mission["promotion"]
    repository = promotion["repository"]
    if (push or open_pr) and confirm_repo != repository:
        raise RecursiveCampaignError(
            f"--confirm-repo must exactly match promotion repository {repository!r}"
        )
    if open_pr and not push:
        raise RecursiveCampaignError("--open-pr requires --push")

    provider = provider or CodexProvider(
        model=mission.get("codex", {}).get("model"),
        timeout_seconds=int(mission.get("codex", {}).get("timeout_seconds", 3600)),
    )
    provider_preflight = provider.preflight()
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    run_id = f"{mission['mission_id']}-{timestamp}"
    root = (output_root or source_repo / ".prometheus" / "recursive") / run_id
    root.mkdir(parents=True, exist_ok=False)
    mission_snapshot = root / "mission.json"
    mission_snapshot.write_text(json.dumps(mission, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    ledger = EventLedger(root / "events.jsonl")

    publisher = publisher or CaseStudyPublisher(evidence_path=root / "serverforge-publications.json")
    if publisher.evidence_path is None:
        publisher.evidence_path = root / "serverforge-publications.json"
    publisher_status = publisher.preflight()
    ledger.append(
        "mission.accepted",
        {
            "mission_id": mission["mission_id"],
            "mission_sha256": sha256_file(mission_snapshot),
            "source_repo": str(source_repo),
            "provider": provider_preflight,
            "publisher": publisher_status,
        },
    )
    publisher.publish({"type": "mission.accepted", "mission_id": mission["mission_id"], "run_id": run_id})

    base_ref = mission.get("base_ref", "HEAD")
    base_commit = _git(source_repo, "rev-parse", base_ref).stdout.strip()
    worktree_root = root / "worktrees"
    worktree_root.mkdir(parents=True)
    for candidate in mission["candidates"]:
        candidate_id = candidate["id"]
        branch = f"prometheus/candidate/{_slug(run_id)}/{_slug(candidate_id)}"
        workspace = worktree_root / candidate_id
        _git(source_repo, "worktree", "add", "-b", branch, str(workspace), base_commit)
        ledger.append("candidate.workspace_created", {"candidate_id": candidate_id, "branch": branch})

    results: list[dict[str, Any]] = []
    workers = min(
        len(mission["candidates"]),
        int(mission.get("policy", {}).get("parallel_candidates", 3)),
    )
    with ThreadPoolExecutor(max_workers=max(workers, 1)) as executor:
        futures = {
            executor.submit(
                _candidate_worker,
                source_repo,
                root,
                run_id,
                mission,
                candidate,
                provider,
                publisher,
            ): candidate["id"]
            for candidate in mission["candidates"]
        }
        for future in as_completed(futures):
            result = future.result()
            results.append(result)
            ledger.append("candidate.completed", _portable_candidate(result))
    results.sort(key=lambda item: item["candidate_id"])
    (root / "candidate-results.json").write_text(
        json.dumps(results, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )

    viable = [result for result in results if result.get("passed")]
    if not viable:
        raise RecursiveCampaignError("no Codex candidate passed the standard gate")
    leader = sorted(viable, key=lambda item: (-item["score"], item["candidate_id"]))[0]
    candidate = next(item for item in mission["candidates"] if item["id"] == leader["candidate_id"])
    leader_workspace = Path(leader["workspace"])
    ledger.append("leader.selected", {"candidate_id": leader["candidate_id"], "score": leader["score"]})
    publisher.publish({"type": "leader.selected", "candidate_id": leader["candidate_id"], "score": leader["score"]})

    publisher.publish({"type": "challenge.started", "candidate_id": leader["candidate_id"]})
    challenge_execution = provider.challenge(
        leader_workspace,
        mission,
        candidate,
        leader,
        root / "codex",
        publisher.publish,
    )
    repair_files = _changed_files(leader_workspace)
    repair_commit = None
    if repair_files:
        repair_commit = _commit(leader_workspace, f"repair({leader['candidate_id']}): adversarial findings")
        ledger.append(
            "leader.repaired",
            {"candidate_id": leader["candidate_id"], "commit": repair_commit, "files": repair_files},
        )
        publisher.publish(
            {
                "type": "repair.completed",
                "candidate_id": leader["candidate_id"],
                "commit": repair_commit[:12],
                "changed_files": len(repair_files),
            }
        )

    standard_after = _run_gate(mission["standard_test"], leader_workspace, mission)
    challenge_after = _run_gate(mission["challenge_test"], leader_workspace, mission)
    ledger.append(
        "leader.challenged",
        {
            "candidate_id": leader["candidate_id"],
            "standard": standard_after.to_dict(),
            "challenge": challenge_after.to_dict(),
            "codex": challenge_execution.to_dict(),
        },
    )
    publisher.publish(
        {
            "type": "challenge.completed",
            "candidate_id": leader["candidate_id"],
            "standard_passed": standard_after.passed,
            "challenge_passed": challenge_after.passed,
        }
    )
    if not standard_after.passed or not challenge_after.passed:
        raise RecursiveCampaignError("leader failed post-adversarial promotion gates")

    promoted_source_commit = _git(leader_workspace, "rev-parse", "HEAD").stdout.strip()
    artifacts = _source_manifest(leader_workspace)
    ledger.append(
        "candidate.promoted",
        {
            "candidate_id": leader["candidate_id"],
            "source_commit": promoted_source_commit,
            "artifact_count": len(artifacts),
        },
    )
    transcript_evidence = []
    for path in sorted((root / "codex").glob("*")):
        if path.is_file():
            transcript_evidence.append(
                {"path": path.relative_to(root).as_posix(), "sha256": sha256_file(path), "bytes": path.stat().st_size}
            )
    portable_results = [_portable_candidate(result) for result in results]
    promotion_branch = f"{promotion.get('branch_prefix', 'prometheus/recursive')}/{_slug(run_id)}"
    payload = {
        "schema": "prometheus.recursive-receipt.v1",
        "run_id": run_id,
        "mission_id": mission["mission_id"],
        "objective": mission["objective"],
        "created_at": datetime.now(timezone.utc).isoformat(),
        "mission_sha256": sha256_file(mission_snapshot),
        "base_commit": base_commit,
        "candidate_results": portable_results,
        "leader": leader["candidate_id"],
        "adversarial_repair_commit": repair_commit,
        "promoted_source_commit": promoted_source_commit,
        "promotion_branch": promotion_branch,
        "artifacts": artifacts,
        "codex_evidence": transcript_evidence,
        "event_ledger": {
            "path": "events.jsonl",
            "events": ledger.index,
            "chain_head": ledger.head,
            "sha256": sha256_file(ledger.path),
        },
        "serverforge": {
            "live": publisher.live,
            "publication_count": len(publisher.publications),
        },
    }
    receipt = payload | {"receipt_hash": sha256_text(canonical_json(payload))}
    proof_dir = leader_workspace / "proof" / "recursive" / run_id
    proof_dir.mkdir(parents=True, exist_ok=False)
    shutil.copy2(ledger.path, proof_dir / "events.jsonl")
    (proof_dir / "mission.json").write_text(
        json.dumps(mission, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    (proof_dir / "candidate-results.json").write_text(
        json.dumps(portable_results, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    (proof_dir / "codex-evidence.json").write_text(
        json.dumps(transcript_evidence, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    receipt_path = proof_dir / "promotion-receipt.json"
    receipt_path.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    genome = {
        "schema": "prometheus.capability-genome.v1",
        "run_id": run_id,
        "mission_id": mission["mission_id"],
        "promoted_candidate": leader["candidate_id"],
        "capabilities": [
            "parallel-codex-candidate-generation",
            "isolated-self-repository-worktrees",
            "adversarial-codex-repair",
            "test-gated-git-promotion",
            "hash-bound-recursive-receipt",
            "serverforge-live-case-study-telemetry" if publisher.live else "serverforge-offline-case-study-ledger",
        ],
        "evidence_receipt_hash": receipt["receipt_hash"],
    }
    (proof_dir / "capability-genome.json").write_text(
        json.dumps(genome, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    evidence_commit = _commit(leader_workspace, f"proof: bind recursive campaign {run_id}")

    pr_url = None
    if push:
        _git(leader_workspace, "push", "-u", "origin", f"HEAD:refs/heads/{promotion_branch}")
    pr_body = root / "draft-pr.md"
    pr_body.write_text(
        "\n".join(
            [
                f"## PROMETHEUS recursive campaign `{run_id}`",
                "",
                f"- Mission: `{mission['mission_id']}`",
                f"- Leader: `{leader['candidate_id']}`",
                f"- Base commit: `{base_commit}`",
                f"- Promoted source commit: `{promoted_source_commit}`",
                f"- Evidence commit: `{evidence_commit}`",
                f"- Receipt: `{receipt['receipt_hash']}`",
                f"- ServerForge live publication: `{publisher.live}`",
                "",
                "### Validation",
                "",
                f"- Standard gate: `{standard_after.passed}`",
                f"- Adversarial gate: `{challenge_after.passed}`",
                f"- Candidates evaluated: `{len(results)}`",
                "",
                "The committed proof bundle contains the frozen mission, candidate results, capability genome, and promotion receipt.",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    if open_pr:
        pr_url = _open_draft_pr(
            leader_workspace,
            repository,
            promotion_branch,
            promotion.get("base_branch", "main"),
            promotion.get("pr_title", f"PROMETHEUS recursive campaign {mission['mission_id']}"),
            pr_body,
        )

    publisher.publish(
        {
            "type": "promotion.completed",
            "run_id": run_id,
            "leader": leader["candidate_id"],
            "receipt": receipt["receipt_hash"],
            "branch": promotion_branch,
        }
    )
    summary = {
        "status": "PROMOTED",
        "run_id": run_id,
        "mission_id": mission["mission_id"],
        "leader": leader["candidate_id"],
        "receipt_hash": receipt["receipt_hash"],
        "receipt": str(receipt_path),
        "capability_genome": str(proof_dir / "capability-genome.json"),
        "promotion_branch": promotion_branch,
        "promoted_source_commit": promoted_source_commit,
        "evidence_commit": evidence_commit,
        "pushed": push,
        "draft_pr": pr_url,
        "serverforge_live": publisher.live,
        "serverforge_messages": len(publisher.publications),
        "evidence_root": str(root),
        "promoted_workspace": str(leader_workspace),
    }
    (root / "summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return summary


def verify_recursive_receipt(path: Path, workspace: Path | None = None) -> bool:
    path = path.resolve()
    receipt = json.loads(path.read_text(encoding="utf-8"))
    expected = receipt.pop("receipt_hash", None)
    if not expected or expected != sha256_text(canonical_json(receipt)):
        return False
    if workspace is None:
        try:
            workspace = path.parents[3]
        except IndexError:
            return False
    workspace = workspace.resolve()
    ledger_info = receipt.get("event_ledger", {})
    ledger_path = path.parent / ledger_info.get("path", "")
    if not ledger_path.is_file() or sha256_file(ledger_path) != ledger_info.get("sha256"):
        return False
    lines = ledger_path.read_text(encoding="utf-8").splitlines()
    if len(lines) != ledger_info.get("events") or not verify_ledger(ledger_path):
        return False
    if json.loads(lines[-1]).get("event_hash") != ledger_info.get("chain_head"):
        return False
    for artifact in receipt.get("artifacts", []):
        artifact_path = (workspace / artifact["path"]).resolve()
        if workspace not in artifact_path.parents or not artifact_path.is_file():
            return False
        if sha256_file(artifact_path) != artifact["sha256"] or artifact_path.stat().st_size != artifact["bytes"]:
            return False
    return True

#!/usr/bin/env python3
"""Judge-facing verifier for the real PROMETHEUS P0 Command-to-Proof loop."""

from __future__ import annotations

import hashlib
import json
import platform
import shutil
import subprocess
import sys
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def write_json(path: Path, value: Any) -> None:
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def main() -> int:
    started = time.perf_counter()
    script = Path(__file__).resolve()
    root = script.parents[2]
    if not (root / "pyproject.toml").is_file() or not (root / "missions/bootstrap.json").is_file():
        print("[FAIL] repository root discovery", file=sys.stderr)
        return 2

    sys.path.insert(0, str(root / "src"))
    from prometheus_kernel.engine import execute_mission, verify_receipt

    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    demo_id = f"OMEGA-{stamp}-{uuid.uuid4().hex[:8]}"
    demo_root = root / "competition" / "demo" / "evidence" / demo_id
    campaign_root = demo_root / "campaign"
    demo_root.mkdir(parents=True)
    transcript = demo_root / "judge-transcript.log"
    gates: list[dict[str, Any]] = []

    def gate(name: str, passed: bool, evidence: str, detail: str) -> None:
        status = "PASS" if passed else "FAIL"
        line = f"[{status}] {name}: {detail} | evidence={evidence}"
        print(line)
        with transcript.open("a", encoding="utf-8") as stream:
            stream.write(line + "\n")
        gates.append({"gate": name, "passed": passed, "evidence": evidence, "detail": detail})
        if not passed:
            raise RuntimeError(f"gate failed: {name}")

    try:
        gate("repository-root", True, "pyproject.toml", str(root))
        py_ok = sys.version_info >= (3, 11)
        git = subprocess.run(["git", "--version"], text=True, capture_output=True, check=False)
        gate("runtime", py_ok, transcript.relative_to(root).as_posix(), f"Python {platform.python_version()} (requires >=3.11)")
        gate("dependency-git", git.returncode == 0, transcript.relative_to(root).as_posix(), git.stdout.strip() or git.stderr.strip())

        regression_log = demo_root / "kernel-regression.log"
        regression_started = time.perf_counter()
        regression = subprocess.run(
            [sys.executable, "-m", "unittest", "discover", "-s", "tests", "-v"],
            cwd=root, text=True, capture_output=True, check=False,
            env={"PYTHONPATH": str(root / "src"), "PATH": __import__("os").environ.get("PATH", ""), "PYTHONUTF8": "1"},
        )
        regression_log.write_text(regression.stdout + regression.stderr, encoding="utf-8")
        gate("kernel-regression", regression.returncode == 0, regression_log.relative_to(root).as_posix(), f"exit={regression.returncode}; duration={time.perf_counter()-regression_started:.3f}s")

        summary = execute_mission(root / "missions" / "bootstrap.json", campaign_root)
        receipt_path = Path(summary["receipt"])
        run_root = receipt_path.parent
        receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
        mission = json.loads((run_root / "mission.json").read_text(encoding="utf-8"))

        candidates = receipt["candidate_results"]
        commits = {item["commit_sha"] for item in candidates}
        strategies = {item["strategy"] for item in candidates}
        gate("distinct-candidates", len(candidates) >= 3 and len(commits) == len(candidates) and len(strategies) == len(candidates), receipt_path.relative_to(root).as_posix(), f"candidates={len(candidates)}; distinct_commits={len(commits)}; distinct_strategies={len(strategies)}")
        gate("real-execution", all(item["standard_test"]["exit_code"] == 0 for item in candidates), receipt_path.relative_to(root).as_posix(), f"standard executions={len(candidates)}")

        leader = next(item for item in candidates if item["candidate_id"] == receipt["leader"])
        attempts = leader["challenge_attempts"]
        gate("adversarial-challenge", len(attempts) == 2 and attempts[0]["exit_code"] != 0, receipt_path.relative_to(root).as_posix(), f"leader={receipt['leader']}; initial_exit={attempts[0]['exit_code']}")
        gate("repair-and-retest", bool(leader["repair_commits"]) and leader["standard_test"]["exit_code"] == 0 and attempts[-1]["exit_code"] == 0, receipt_path.relative_to(root).as_posix(), f"repair_commit={leader['repair_commits'][-1]}; final_standard=0; final_challenge=0")
        gate("proofgrid-receipt", verify_receipt(receipt_path), receipt_path.relative_to(root).as_posix(), f"receipt_hash={receipt['receipt_hash']}")

        tamper_evidence = demo_root / "tamper-evidence-copy"
        shutil.copytree(run_root, tamper_evidence)
        evidence_record = receipt["execution_evidence"][0]
        evidence_target = tamper_evidence / evidence_record["path"]
        with evidence_target.open("a", encoding="utf-8") as stream:
            stream.write("\nTAMPER-PROBE\n")
        gate("evidence-tamper-rejected", not verify_receipt(tamper_evidence / "promotion-receipt.json"), evidence_target.relative_to(root).as_posix(), "verification returned false after evidence mutation")

        tamper_receipt = demo_root / "tamper-receipt-copy"
        shutil.copytree(run_root, tamper_receipt)
        bad_receipt_path = tamper_receipt / "promotion-receipt.json"
        bad_receipt = json.loads(bad_receipt_path.read_text(encoding="utf-8"))
        bad_receipt["leader"] = "TAMPERED"
        write_json(bad_receipt_path, bad_receipt)
        gate("receipt-tamper-rejected", not verify_receipt(bad_receipt_path), bad_receipt_path.relative_to(root).as_posix(), "verification returned false after receipt mutation")

        genome_path = Path(summary["capability_genome"])
        truth_path = Path(summary["build_truth"])
        genome = json.loads(genome_path.read_text(encoding="utf-8"))
        truth = json.loads(truth_path.read_text(encoding="utf-8"))
        gate("capability-genome", genome["evidence_receipt_hash"] == receipt["receipt_hash"] and genome["promoted_candidate"] == receipt["leader"], genome_path.relative_to(root).as_posix(), f"candidate={genome['promoted_candidate']}; receipt linked")
        gate("build-truth", truth["state"] == "PROVEN" and truth["receipt_hash"] == receipt["receipt_hash"] and truth["external_claims"]["discord_live_deployment"] == "NOT_CLAIMED", truth_path.relative_to(root).as_posix(), "state=PROVEN; external live deployment not claimed")

        artifacts = []
        for path in sorted(p for p in demo_root.rglob("*") if p.is_file()):
            artifacts.append({"path": path.relative_to(root).as_posix(), "bytes": path.stat().st_size, "sha256": sha256(path)})
        result = {
            "schema": "prometheus.omega.demo-result.v1", "demo_id": demo_id,
            "mission": mission["mission_id"], "status": "PROMETHEUS OMEGA PROVEN",
            "duration_seconds": round(time.perf_counter() - started, 6), "gates": gates,
            "receipt": receipt_path.relative_to(root).as_posix(), "receipt_hash": receipt["receipt_hash"],
            "artifact_count_before_result": len(artifacts),
        }
        result_path = demo_root / "OMEGA_RESULT.json"
        write_json(result_path, result)
        artifacts.append({"path": result_path.relative_to(root).as_posix(), "bytes": result_path.stat().st_size, "sha256": sha256(result_path)})
        write_json(demo_root / "ARTIFACT_INDEX.json", {"schema": "prometheus.omega.artifact-index.v1", "demo_id": demo_id, "artifacts": artifacts})
        print(f"\nPROMETHEUS OMEGA PROVEN\nEvidence: {demo_root.relative_to(root)}\nReceipt: {receipt_path.relative_to(root)}")
        return 0
    except Exception as error:
        print(f"\nPROMETHEUS OMEGA NOT PROVEN: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

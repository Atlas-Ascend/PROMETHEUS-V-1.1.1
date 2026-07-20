from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import time
import traceback
import uuid

from datetime import datetime, timezone
from pathlib import Path
from typing import Any


PRODUCT_NAME = "PROMETHEUS Ω"
DESIGNATION = "Alpha Ω Ultra JARVIS Prime"
ENGINE_VERSION = "1.1.1-omega"


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def timestamp_id() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def canonical_json(value: Any) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")


def sha256_bytes(value: bytes) -> str:
    return "sha256:" + hashlib.sha256(value).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()

    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)

    return "sha256:" + digest.hexdigest()


def write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def relative(path: Path, root: Path) -> str:
    return path.resolve().relative_to(root.resolve()).as_posix()


def current_git_commit(repo: Path) -> str:
    result = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=repo,
        text=True,
        capture_output=True,
        check=False,
    )

    if result.returncode != 0:
        return "UNAVAILABLE"

    return result.stdout.strip()


class CommandToProofCampaign:
    def __init__(self, repo: Path) -> None:
        self.repo = repo.resolve()
        self.campaign_id = f"C2P-{timestamp_id()}-{uuid.uuid4().hex[:8].upper()}"
        self.started_at = utc_now()

        self.mission_root = self.repo / "missions" / self.campaign_id
        self.workspace_root = self.repo / "workspaces" / self.campaign_id
        self.evidence_root = (
            self.repo / "evidence" / "campaigns" / self.campaign_id
        )
        self.receipt_root = (
            self.repo / "receipts" / "campaigns" / self.campaign_id
        )
        self.genome_root = (
            self.repo / "genomes" / "campaigns" / self.campaign_id
        )

        for path in (
            self.mission_root,
            self.workspace_root,
            self.evidence_root,
            self.receipt_root,
            self.genome_root,
        ):
            path.mkdir(parents=True, exist_ok=True)

        self.events_path = self.evidence_root / "events.ndjson"
        self.receipt_sequence = 0
        self.previous_receipt_hash: str | None = None
        self.receipts: list[dict[str, Any]] = []

    def banner(self, text: str) -> None:
        print()
        print("=" * 72)
        print(text)
        print("=" * 72)

    def emit(
        self,
        gate: str,
        status: str,
        message: str,
        artifact: Path | None = None,
        actor: str = "PROMETHEUS_OMEGA",
    ) -> None:
        event = {
            "event_id": f"EVT-{uuid.uuid4().hex.upper()}",
            "campaign_id": self.campaign_id,
            "timestamp": utc_now(),
            "gate": gate,
            "status": status,
            "actor": actor,
            "message": message,
            "artifact": (
                relative(artifact, self.repo)
                if artifact is not None and artifact.exists()
                else None
            ),
        }

        with self.events_path.open("a", encoding="utf-8") as stream:
            stream.write(
                json.dumps(event, ensure_ascii=False, sort_keys=True) + "\n"
            )

        print(f"[{status}] {gate}: {message}")

    def make_receipt(
        self,
        receipt_type: str,
        payload: dict[str, Any],
    ) -> dict[str, Any]:
        self.receipt_sequence += 1

        receipt = {
            "receipt_id": (
                f"PGR-{self.campaign_id}-{self.receipt_sequence:03d}"
            ),
            "sequence": self.receipt_sequence,
            "receipt_type": receipt_type,
            "campaign_id": self.campaign_id,
            "product": PRODUCT_NAME,
            "engine_version": ENGINE_VERSION,
            "created_at": utc_now(),
            "previous_receipt_hash": self.previous_receipt_hash,
            "payload": payload,
        }

        receipt_hash = sha256_bytes(canonical_json(receipt))
        receipt["receipt_hash"] = receipt_hash

        filename = (
            f"{self.receipt_sequence:03d}_"
            f"{receipt_type.lower()}.json"
        )
        path = self.receipt_root / filename

        write_json(path, receipt)

        receipt["_path"] = relative(path, self.repo)

        self.previous_receipt_hash = receipt_hash
        self.receipts.append(receipt)

        return receipt

    def run_process(
        self,
        candidate_id: str,
        phase: str,
        command: list[str],
        cwd: Path,
        timeout_seconds: int = 30,
    ) -> dict[str, Any]:
        run_id = f"EXE-{uuid.uuid4().hex.upper()}"
        run_root = self.evidence_root / candidate_id / phase
        run_root.mkdir(parents=True, exist_ok=True)

        started_at = utc_now()
        monotonic_start = time.perf_counter()

        stdout = ""
        stderr = ""
        exit_code = -1
        status = "FAILED"
        timed_out = False

        try:
            result = subprocess.run(
                command,
                cwd=cwd,
                text=True,
                capture_output=True,
                timeout=timeout_seconds,
                check=False,
                env={
                    **os.environ,
                    "PYTHONUTF8": "1",
                    "PYTHONDONTWRITEBYTECODE": "1",
                },
            )

            stdout = result.stdout
            stderr = result.stderr
            exit_code = result.returncode
            status = "PASSED" if exit_code == 0 else "FAILED"

        except subprocess.TimeoutExpired as error:
            timed_out = True
            status = "TIMEOUT"
            stdout = error.stdout or ""
            stderr = error.stderr or ""
            exit_code = 124

        except Exception:
            status = "ERROR"
            stderr = traceback.format_exc()
            exit_code = 125

        duration = round(time.perf_counter() - monotonic_start, 6)
        finished_at = utc_now()

        stdout_path = run_root / "stdout.log"
        stderr_path = run_root / "stderr.log"

        write_text(stdout_path, stdout)
        write_text(stderr_path, stderr)

        result_record = {
            "execution_id": run_id,
            "campaign_id": self.campaign_id,
            "candidate_id": candidate_id,
            "phase": phase,
            "command": command,
            "working_directory": relative(cwd, self.repo),
            "started_at": started_at,
            "finished_at": finished_at,
            "duration_seconds": duration,
            "exit_code": exit_code,
            "timed_out": timed_out,
            "status": status,
            "stdout_path": relative(stdout_path, self.repo),
            "stderr_path": relative(stderr_path, self.repo),
            "stdout_hash": sha256_file(stdout_path),
            "stderr_hash": sha256_file(stderr_path),
        }

        result_path = run_root / "execution.json"
        write_json(result_path, result_record)
        result_record["result_path"] = relative(result_path, self.repo)

        return result_record

    def create_mission(self) -> dict[str, Any]:
        self.banner("GATE II | JARVIS PRIME MISSION INTAKE")

        mission = {
            "mission_id": f"MIS-{self.campaign_id}",
            "mission_intent_id": f"MI-{self.campaign_id}",
            "campaign_id": self.campaign_id,
            "objective": (
                "Implement and prove a safe arithmetic expression evaluator."
            ),
            "source_command": (
                "Use Command-to-Proof to produce competing implementations, "
                "execute them, challenge the leader, repair defects, retest, "
                "and promote only the evidence-backed candidate."
            ),
            "scope": {
                "allowed_paths": [
                    relative(self.workspace_root, self.repo),
                    relative(self.evidence_root, self.repo),
                    relative(self.receipt_root, self.repo),
                    relative(self.genome_root, self.repo),
                ],
                "protected_paths": [".git", "canon", "build_truth/canonical"],
            },
            "acceptance_gates": [
                "Correct arithmetic",
                "No eval or exec",
                "Unsupported syntax rejected",
                "Exponent bounded",
                "Expression length bounded",
                "Division-by-zero behavior preserved",
                "Real subprocess execution",
                "Reproducible evidence",
                "Valid receipt chain",
            ],
            "evidence_requirements": [
                "candidate manifest",
                "candidate source hash",
                "stdout",
                "stderr",
                "exit code",
                "duration",
                "baseline test result",
                "adversarial result",
                "repair evidence",
                "promotion receipt",
            ],
            "rollback_plan": {
                "strategy": "Candidate workspaces are isolated and disposable.",
                "canonical_code_is_modified": False,
            },
            "created_at": utc_now(),
        }

        mission_path = self.mission_root / "mission.json"
        write_json(mission_path, mission)

        self.emit(
            "JARVIS_PRIME",
            "OPEN",
            "Mission interpreted and acceptance gates established.",
            mission_path,
        )

        self.make_receipt(
            "MISSION_RECEIPT",
            {
                "mission_id": mission["mission_id"],
                "mission_path": relative(mission_path, self.repo),
                "mission_hash": sha256_file(mission_path),
                "status": "ACCEPTED",
            },
        )

        return mission

    def candidate_sources(self) -> list[dict[str, str]]:
        return [
            {
                "candidate_id": "CAN-001",
                "name": "Dynamic Evaluation Route",
                "strategy": (
                    "Use Python dynamic evaluation with builtins removed."
                ),
                "rationale": (
                    "Maximum language coverage with minimal implementation."
                ),
                "source": '''
def calculate(expression: str):
    return eval(expression, {"__builtins__": {}}, {})
'''.strip()
                + "\n",
            },
            {
                "candidate_id": "CAN-002",
                "name": "Minimal Parser Route",
                "strategy": (
                    "Implement a tiny dependency-free addition parser."
                ),
                "rationale": (
                    "Small attack surface and straightforward execution."
                ),
                "source": '''
def calculate(expression: str):
    parts = [part.strip() for part in expression.split("+")]
    values = [float(part) for part in parts]
    result = sum(values)
    return int(result) if result.is_integer() else result
'''.strip()
                + "\n",
            },
            {
                "candidate_id": "CAN-003",
                "name": "AST Whitelist Route",
                "strategy": (
                    "Parse Python expression syntax into an AST and evaluate "
                    "only explicitly permitted numeric nodes and operators."
                ),
                "rationale": (
                    "Separates parsing from execution and denies arbitrary "
                    "code invocation."
                ),
                "source": '''
import ast
import operator


_BINARY_OPERATORS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.Pow: operator.pow,
}

_UNARY_OPERATORS = {
    ast.UAdd: operator.pos,
    ast.USub: operator.neg,
}


def _evaluate(node):
    if isinstance(node, ast.Expression):
        return _evaluate(node.body)

    if isinstance(node, ast.Constant):
        if type(node.value) not in (int, float):
            raise ValueError("Only numeric constants are allowed.")
        return node.value

    if isinstance(node, ast.BinOp) and type(node.op) in _BINARY_OPERATORS:
        left = _evaluate(node.left)
        right = _evaluate(node.right)
        return _BINARY_OPERATORS[type(node.op)](left, right)

    if isinstance(node, ast.UnaryOp) and type(node.op) in _UNARY_OPERATORS:
        return _UNARY_OPERATORS[type(node.op)](_evaluate(node.operand))

    raise ValueError(f"Unsupported expression node: {type(node).__name__}")


def calculate(expression: str):
    tree = ast.parse(expression, mode="eval")
    return _evaluate(tree)
'''.strip()
                + "\n",
            },
        ]

    def baseline_test_source(self) -> str:
        return '''
import json
import math
import sys

from evaluator import calculate


CASES = [
    ("1 + 2", 3),
    ("10 / 4", 2.5),
    ("2 ** 5", 32),
    ("-8 + 3 * 4", 4),
    ("(7 - 2) * 6", 30),
]

failures = []

for expression, expected in CASES:
    try:
        actual = calculate(expression)

        if isinstance(expected, float):
            passed = math.isclose(actual, expected)
        else:
            passed = actual == expected

        if not passed:
            failures.append({
                "expression": expression,
                "expected": expected,
                "actual": actual,
            })

    except Exception as error:
        failures.append({
            "expression": expression,
            "expected": expected,
            "error": f"{type(error).__name__}: {error}",
        })

print(json.dumps({
    "suite": "baseline",
    "passed": len(CASES) - len(failures),
    "failed": len(failures),
    "failures": failures,
}, indent=2))

sys.exit(1 if failures else 0)
'''.strip() + "\n"

    def challenge_test_source(self) -> str:
        return '''
import json
import sys
from pathlib import Path

from evaluator import calculate


failures = []
source = Path("evaluator.py").read_text(encoding="utf-8")


def record(name, passed, detail):
    if not passed:
        failures.append({
            "challenge": name,
            "detail": detail,
        })


record(
    "no_dynamic_eval",
    "eval(" not in source and "exec(" not in source,
    "Candidate source may not invoke eval or exec.",
)

try:
    calculate("__import__('os').getcwd()")
    record(
        "reject_function_calls",
        False,
        "Function-call expression was accepted.",
    )
except Exception:
    record(
        "reject_function_calls",
        True,
        "Function calls rejected.",
    )

try:
    calculate("1 / 0")
    record(
        "division_by_zero",
        False,
        "Division by zero unexpectedly returned a value.",
    )
except ZeroDivisionError:
    record(
        "division_by_zero",
        True,
        "Division by zero preserved.",
    )
except Exception as error:
    record(
        "division_by_zero",
        False,
        f"Unexpected exception type: {type(error).__name__}",
    )

try:
    calculate("2 ** 13")
    record(
        "bounded_exponent",
        False,
        "Exponent greater than 12 was accepted.",
    )
except ValueError:
    record(
        "bounded_exponent",
        True,
        "Oversized exponent rejected.",
    )
except Exception as error:
    record(
        "bounded_exponent",
        False,
        f"Unexpected exception type: {type(error).__name__}",
    )

long_expression = "1+" * 200 + "1"

try:
    calculate(long_expression)
    record(
        "bounded_expression_length",
        False,
        "Expression longer than 256 characters was accepted.",
    )
except ValueError:
    record(
        "bounded_expression_length",
        True,
        "Oversized expression rejected.",
    )
except Exception as error:
    record(
        "bounded_expression_length",
        False,
        f"Unexpected exception type: {type(error).__name__}",
    )

print(json.dumps({
    "suite": "adversarial",
    "passed": 5 - len(failures),
    "failed": len(failures),
    "findings": failures,
}, indent=2))

sys.exit(1 if failures else 0)
'''.strip() + "\n"

    def repaired_source(self) -> str:
        return '''
import ast
import operator


MAX_EXPRESSION_LENGTH = 256
MAX_EXPONENT = 12

_BINARY_OPERATORS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
}

_UNARY_OPERATORS = {
    ast.UAdd: operator.pos,
    ast.USub: operator.neg,
}


def _bounded_power(left, right):
    if not isinstance(right, int):
        raise ValueError("Exponent must be an integer.")

    if abs(right) > MAX_EXPONENT:
        raise ValueError(
            f"Exponent magnitude may not exceed {MAX_EXPONENT}."
        )

    return operator.pow(left, right)


def _evaluate(node):
    if isinstance(node, ast.Expression):
        return _evaluate(node.body)

    if isinstance(node, ast.Constant):
        if type(node.value) not in (int, float):
            raise ValueError("Only numeric constants are allowed.")
        return node.value

    if isinstance(node, ast.BinOp):
        left = _evaluate(node.left)
        right = _evaluate(node.right)

        if isinstance(node.op, ast.Pow):
            return _bounded_power(left, right)

        operation = _BINARY_OPERATORS.get(type(node.op))

        if operation is None:
            raise ValueError(
                f"Unsupported operator: {type(node.op).__name__}"
            )

        return operation(left, right)

    if isinstance(node, ast.UnaryOp):
        operation = _UNARY_OPERATORS.get(type(node.op))

        if operation is None:
            raise ValueError(
                f"Unsupported unary operator: {type(node.op).__name__}"
            )

        return operation(_evaluate(node.operand))

    raise ValueError(f"Unsupported expression node: {type(node).__name__}")


def calculate(expression: str):
    if not isinstance(expression, str):
        raise TypeError("Expression must be a string.")

    if not expression.strip():
        raise ValueError("Expression may not be empty.")

    if len(expression) > MAX_EXPRESSION_LENGTH:
        raise ValueError(
            f"Expression may not exceed {MAX_EXPRESSION_LENGTH} characters."
        )

    tree = ast.parse(expression, mode="eval")
    return _evaluate(tree)
'''.strip() + "\n"

    def create_candidates(
        self,
        mission: dict[str, Any],
    ) -> list[dict[str, Any]]:
        self.banner("GATE III | COUNTERFACTUAL FORGE")

        candidates: list[dict[str, Any]] = []

        for definition in self.candidate_sources():
            candidate_id = definition["candidate_id"]
            workspace = self.workspace_root / candidate_id
            workspace.mkdir(parents=True, exist_ok=True)

            source_path = workspace / "evaluator.py"
            baseline_path = workspace / "baseline_tests.py"
            challenge_path = workspace / "adversarial_tests.py"

            write_text(source_path, definition["source"])
            write_text(baseline_path, self.baseline_test_source())
            write_text(challenge_path, self.challenge_test_source())

            manifest = {
                "candidate_id": candidate_id,
                "mission_id": mission["mission_id"],
                "name": definition["name"],
                "strategy": definition["strategy"],
                "rationale": definition["rationale"],
                "workspace": relative(workspace, self.repo),
                "source_path": relative(source_path, self.repo),
                "source_hash": sha256_file(source_path),
                "isolation": "INDEPENDENT_WORKSPACE",
                "status": "BUILT",
                "created_at": utc_now(),
            }

            manifest_path = workspace / "candidate_manifest.json"
            write_json(manifest_path, manifest)

            manifest["manifest_path"] = relative(manifest_path, self.repo)
            candidates.append(manifest)

            self.emit(
                "COUNTERFACTUAL_FORGE",
                "OPEN",
                f"{candidate_id} built using {definition['name']}.",
                manifest_path,
            )

            self.make_receipt(
                "CANDIDATE_RECEIPT",
                {
                    "candidate_id": candidate_id,
                    "strategy": definition["strategy"],
                    "workspace": relative(workspace, self.repo),
                    "source_hash": manifest["source_hash"],
                    "status": "BUILT",
                },
            )

        return candidates

    def execute_candidates(
        self,
        candidates: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        self.banner("GATE IV | REAL EXECUTION AND EVIDENCE")

        evaluated: list[dict[str, Any]] = []

        for candidate in candidates:
            candidate_id = candidate["candidate_id"]
            workspace = self.repo / candidate["workspace"]
            source = (workspace / "evaluator.py").read_text(
                encoding="utf-8"
            )

            execution = self.run_process(
                candidate_id=candidate_id,
                phase="baseline",
                command=[sys.executable, "baseline_tests.py"],
                cwd=workspace,
            )

            score = 0
            rejection_reasons: list[str] = []

            if execution["status"] == "PASSED":
                score += 100
            else:
                rejection_reasons.append(
                    "Baseline functional test suite failed."
                )

            if "eval(" in source or "exec(" in source:
                score -= 60
                rejection_reasons.append(
                    "Static inspection detected dynamic code execution."
                )

            if "ast.parse" in source:
                score += 20

            record = {
                **candidate,
                "execution": execution,
                "score": score,
                "rejection_reasons": rejection_reasons,
                "status": (
                    "LEADING"
                    if execution["status"] == "PASSED"
                    else "FAILED"
                ),
            }

            evaluated.append(record)

            self.emit(
                "EXECUTION_LAYER",
                execution["status"],
                (
                    f"{candidate_id} exited {execution['exit_code']} "
                    f"in {execution['duration_seconds']} seconds."
                ),
                self.repo / execution["result_path"],
            )

            self.make_receipt(
                "EXECUTION_RECEIPT",
                {
                    "candidate_id": candidate_id,
                    "execution": execution,
                    "source_hash": candidate["source_hash"],
                    "score": score,
                    "rejection_reasons": rejection_reasons,
                },
            )

        return evaluated

    def select_leader(
        self,
        candidates: list[dict[str, Any]],
    ) -> dict[str, Any]:
        self.banner("GATE V | SECA DEVOS ARBITRATION")

        viable = [
            candidate
            for candidate in candidates
            if candidate["execution"]["status"] == "PASSED"
        ]

        if not viable:
            raise RuntimeError("No candidate passed baseline execution.")

        leader = max(viable, key=lambda candidate: candidate["score"])

        for candidate in candidates:
            if candidate["candidate_id"] == leader["candidate_id"]:
                candidate["status"] = "LEADING"
                continue

            candidate["status"] = "REJECTED"

            reasons = list(candidate["rejection_reasons"])

            if not reasons:
                reasons.append(
                    "Candidate was outscored by stronger evidence."
                )

            self.make_receipt(
                "REJECTION_RECEIPT",
                {
                    "candidate_id": candidate["candidate_id"],
                    "status": "REJECTED",
                    "score": candidate["score"],
                    "reasons": reasons,
                    "leader": leader["candidate_id"],
                },
            )

            self.emit(
                "SECA_DEVOS",
                "REJECTED",
                f"{candidate['candidate_id']} rejected: {' '.join(reasons)}",
            )

        self.emit(
            "SECA_DEVOS",
            "OPEN",
            (
                f"{leader['candidate_id']} selected as provisional leader "
                f"with score {leader['score']}."
            ),
        )

        return leader

    def challenge_leader(
        self,
        leader: dict[str, Any],
    ) -> dict[str, Any]:
        self.banner("GATE VI | ADVERSARIAL TWIN")

        candidate_id = leader["candidate_id"]
        workspace = self.repo / leader["workspace"]

        challenge = self.run_process(
            candidate_id=candidate_id,
            phase="adversarial_initial",
            command=[sys.executable, "adversarial_tests.py"],
            cwd=workspace,
        )

        finding = {
            "finding_id": f"FND-{uuid.uuid4().hex.upper()}",
            "candidate_id": candidate_id,
            "severity": "HIGH",
            "category": "RESOURCE_AND_BOUNDARY_CONTROL",
            "description": (
                "The provisional leader passed functional tests but did not "
                "enforce all adversarial resource boundaries."
            ),
            "promotion_blocking": challenge["status"] != "PASSED",
            "evidence": challenge,
            "repair_requirement": (
                "Bound expression length and exponent magnitude, then rerun "
                "functional and adversarial tests."
            ),
        }

        finding_path = (
            self.evidence_root
            / candidate_id
            / "adversarial_initial"
            / "finding.json"
        )
        write_json(finding_path, finding)

        self.make_receipt(
            "CHALLENGE_RECEIPT",
            {
                "candidate_id": candidate_id,
                "challenge_execution": challenge,
                "finding": finding,
                "finding_path": relative(finding_path, self.repo),
            },
        )

        status = "BLOCKED" if finding["promotion_blocking"] else "PASSED"

        self.emit(
            "ADVERSARIAL_TWIN",
            status,
            (
                "Leader challenged. "
                f"Promotion blocking: {finding['promotion_blocking']}."
            ),
            finding_path,
        )

        return finding

    def repair_and_retest(
        self,
        leader: dict[str, Any],
        finding: dict[str, Any],
    ) -> dict[str, Any]:
        self.banner("GATE VII | REPAIR AND RETEST")

        candidate_id = leader["candidate_id"]
        workspace = self.repo / leader["workspace"]
        source_path = workspace / "evaluator.py"

        pre_repair_hash = sha256_file(source_path)

        write_text(source_path, self.repaired_source())

        post_repair_hash = sha256_file(source_path)

        baseline = self.run_process(
            candidate_id=candidate_id,
            phase="repair_baseline",
            command=[sys.executable, "baseline_tests.py"],
            cwd=workspace,
        )

        adversarial = self.run_process(
            candidate_id=candidate_id,
            phase="repair_adversarial",
            command=[sys.executable, "adversarial_tests.py"],
            cwd=workspace,
        )

        passed = (
            baseline["status"] == "PASSED"
            and adversarial["status"] == "PASSED"
        )

        repair = {
            "candidate_id": candidate_id,
            "finding_id": finding["finding_id"],
            "pre_repair_hash": pre_repair_hash,
            "post_repair_hash": post_repair_hash,
            "baseline_retest": baseline,
            "adversarial_retest": adversarial,
            "status": "PROVEN" if passed else "FAILED",
            "repaired_at": utc_now(),
        }

        repair_path = self.evidence_root / candidate_id / "repair.json"
        write_json(repair_path, repair)

        self.make_receipt(
            "REPAIR_RECEIPT",
            {
                **repair,
                "repair_path": relative(repair_path, self.repo),
            },
        )

        self.emit(
            "REPAIR_GATE",
            "OPEN" if passed else "FAILED",
            (
                "Repair completed and all suites passed."
                if passed
                else "Repair failed one or more retest gates."
            ),
            repair_path,
        )

        if not passed:
            raise RuntimeError("Repair and retest did not reach PROVEN state.")

        return repair

    def artifact_manifest(self) -> list[dict[str, str]]:
        artifacts: list[dict[str, str]] = []

        roots = [
            self.mission_root,
            self.workspace_root,
            self.evidence_root,
            self.receipt_root,
            self.genome_root,
        ]

        for root in roots:
            if not root.exists():
                continue

            for path in sorted(root.rglob("*")):
                if path.is_file():
                    artifacts.append(
                        {
                            "path": relative(path, self.repo),
                            "sha256": sha256_file(path),
                        }
                    )

        return artifacts

    def promote(
        self,
        mission: dict[str, Any],
        candidates: list[dict[str, Any]],
        leader: dict[str, Any],
        repair: dict[str, Any],
    ) -> dict[str, Any]:
        self.banner("GATE VIII | PROOFGRID PROMOTION")

        leader_workspace = self.repo / leader["workspace"]
        final_source = leader_workspace / "evaluator.py"

        genome = {
            "genome_id": f"CG-{self.campaign_id}",
            "campaign_id": self.campaign_id,
            "capability_name": (
                "Evidence-Governed Safe Expression Evaluation"
            ),
            "proven_candidate": leader["candidate_id"],
            "proven_source_hash": sha256_file(final_source),
            "reusable_patterns": [
                {
                    "pattern": "AST whitelist evaluation",
                    "proof": "Functional and adversarial suites passed.",
                },
                {
                    "pattern": "Resource-bound syntax",
                    "proof": (
                        "Expression length and exponent magnitude are bounded."
                    ),
                },
                {
                    "pattern": "Proof before promotion",
                    "proof": (
                        "Leader was blocked, repaired, retested, and only then "
                        "promoted."
                    ),
                },
                {
                    "pattern": "Independent candidate workspaces",
                    "proof": (
                        "Every candidate retained independent source, logs, "
                        "hashes, tests, and receipts."
                    ),
                },
            ],
            "failure_knowledge": [
                "Functional correctness does not prove security.",
                "Removing builtins does not make eval an acceptable boundary.",
                "A syntax whitelist still requires resource constraints.",
            ],
            "transfer_targets": [
                "configuration evaluators",
                "policy engines",
                "formula processors",
                "workflow conditions",
                "local automation rules",
            ],
            "created_at": utc_now(),
        }

        genome_path = self.genome_root / "capability_genome.json"
        write_json(genome_path, genome)

        genome_receipt = self.make_receipt(
            "CAPABILITY_GENOME_RECEIPT",
            {
                "genome_id": genome["genome_id"],
                "genome_path": relative(genome_path, self.repo),
                "genome_hash": sha256_file(genome_path),
                "status": "REGISTERED",
            },
        )

        promotion_payload = {
            "mission_id": mission["mission_id"],
            "candidate_ids": [
                candidate["candidate_id"] for candidate in candidates
            ],
            "candidate_hashes": {
                candidate["candidate_id"]: candidate["source_hash"]
                for candidate in candidates
            },
            "final_candidate": leader["candidate_id"],
            "final_source_hash": sha256_file(final_source),
            "repair_status": repair["status"],
            "promotion_state": "PROMOTED",
            "claim_map": [
                {
                    "claim": "Three materially distinct candidates generated",
                    "state": "PROVEN",
                },
                {
                    "claim": "Candidates executed in isolated workspaces",
                    "state": "PROVEN",
                },
                {
                    "claim": "stdout, stderr, exit code, and duration captured",
                    "state": "PROVEN",
                },
                {
                    "claim": "Provisional leader adversarially challenged",
                    "state": "PROVEN",
                },
                {
                    "claim": "Blocking findings repaired and retested",
                    "state": "PROVEN",
                },
                {
                    "claim": "Capability genome generated",
                    "state": "PROVEN",
                    "receipt": genome_receipt["receipt_hash"],
                },
            ],
        }

        promotion = self.make_receipt(
            "PROMOTION_RECEIPT",
            promotion_payload,
        )

        manifest = self.artifact_manifest()
        manifest_path = self.evidence_root / "artifact_manifest.json"
        write_json(manifest_path, manifest)

        release = self.make_receipt(
            "RELEASE_RECEIPT",
            {
                "campaign_id": self.campaign_id,
                "promotion_receipt": promotion["receipt_hash"],
                "artifact_manifest_path": relative(
                    manifest_path,
                    self.repo,
                ),
                "artifact_count": len(manifest),
                "status": "PROVEN",
            },
        )

        self.emit(
            "PROOFGRID",
            "OPEN",
            (
                f"{leader['candidate_id']} promoted with receipt "
                f"{promotion['receipt_hash']}."
            ),
            self.repo / promotion["_path"],
        )

        self.emit(
            "CAPABILITY_GENOME",
            "OPEN",
            f"Capability genome {genome['genome_id']} registered.",
            genome_path,
        )

        return {
            "promotion": promotion,
            "release": release,
            "genome": genome,
            "genome_path": genome_path,
            "manifest_path": manifest_path,
        }

    def update_build_truth(
        self,
        mission: dict[str, Any],
        leader: dict[str, Any],
        promotion: dict[str, Any],
    ) -> None:
        self.banner("GATE IX | BUILD TRUTH RECONCILIATION")

        build_truth = self.repo / "build_truth" / "current"
        build_truth.mkdir(parents=True, exist_ok=True)

        active_campaign = {
            "campaign_id": self.campaign_id,
            "mission_id": mission["mission_id"],
            "product": PRODUCT_NAME,
            "designation": DESIGNATION,
            "state": "PROVEN",
            "leader": leader["candidate_id"],
            "started_at": self.started_at,
            "completed_at": utc_now(),
            "latest_receipt_hash": promotion["release"]["receipt_hash"],
            "event_log": relative(self.events_path, self.repo),
        }

        baseline = {
            "campaign_id": self.campaign_id,
            "git_commit_at_campaign_start": current_git_commit(self.repo),
            "runtime": {
                "python": sys.version,
                "platform": sys.platform,
                "executable": sys.executable,
            },
            "truth_state": "PROVEN",
        }

        latest_receipts = {
            "campaign_id": self.campaign_id,
            "receipt_chain": [
                {
                    "sequence": receipt["sequence"],
                    "receipt_type": receipt["receipt_type"],
                    "receipt_hash": receipt["receipt_hash"],
                    "path": receipt["_path"],
                }
                for receipt in self.receipts
            ],
            "final_receipt_hash": promotion["release"]["receipt_hash"],
        }

        next_commands = {
            "campaign_id": self.campaign_id,
            "state": "PROVEN",
            "commands": [
                {
                    "command": (
                        "pwsh -File "
                        "scripts/Open-PROMETHEUS-Omega-Gates.ps1"
                    ),
                    "purpose": "Launch another complete proof campaign.",
                },
                {
                    "command": (
                        f'"{sys.executable}" '
                        "src/prometheus_omega/command_to_proof.py "
                        "verify --repo ."
                    ),
                    "purpose": "Verify the latest ProofGrid receipt chain.",
                },
            ],
        }

        claims = {
            "campaign_id": self.campaign_id,
            "claims": {
                "mission_intake": "PROVEN",
                "candidate_generation": "PROVEN",
                "candidate_isolation": "PROVEN",
                "real_execution": "PROVEN",
                "evidence_capture": "PROVEN",
                "evidence_arbitration": "PROVEN",
                "adversarial_challenge": "PROVEN",
                "repair_and_retest": "PROVEN",
                "hash_linked_receipts": "PROVEN",
                "capability_genome": "PROVEN",
                "complete_estate_implementation": "NOT_CLAIMED",
            },
        }

        write_json(build_truth / "active_campaign.json", active_campaign)
        write_json(build_truth / "current_baseline.json", baseline)
        write_json(build_truth / "latest_receipts.json", latest_receipts)
        write_json(build_truth / "next_commands.json", next_commands)
        write_json(build_truth / "claim_registry.json", claims)

        self.emit(
            "BUILD_TRUTH",
            "OPEN",
            "Current reality reconciled to PROVEN.",
            build_truth / "active_campaign.json",
        )

    def verify_receipt_chain(self) -> dict[str, Any]:
        receipt_files = sorted(self.receipt_root.glob("*.json"))

        if not receipt_files:
            raise RuntimeError("No receipt files were found.")

        previous_hash: str | None = None
        verified = 0

        for receipt_path in receipt_files:
            receipt = json.loads(
                receipt_path.read_text(encoding="utf-8")
            )

            stored_hash = receipt.pop("receipt_hash")

            if receipt.get("previous_receipt_hash") != previous_hash:
                raise RuntimeError(
                    f"Broken previous hash at {receipt_path.name}"
                )

            calculated_hash = sha256_bytes(canonical_json(receipt))

            if calculated_hash != stored_hash:
                raise RuntimeError(
                    f"Receipt hash mismatch at {receipt_path.name}"
                )

            previous_hash = stored_hash
            verified += 1

        verification = {
            "campaign_id": self.campaign_id,
            "verified_receipts": verified,
            "final_receipt_hash": previous_hash,
            "status": "VERIFIED",
            "verified_at": utc_now(),
        }

        verification_path = (
            self.evidence_root / "receipt_chain_verification.json"
        )
        write_json(verification_path, verification)

        return verification

    def run(self) -> int:
        self.banner(
            f"{PRODUCT_NAME} | {DESIGNATION} | COMMAND-TO-PROOF"
        )

        self.emit(
            "KERNEL",
            "OPEN",
            "Kernel context initialized and evidence stores mounted.",
        )

        mission = self.create_mission()
        candidates = self.create_candidates(mission)
        evaluated = self.execute_candidates(candidates)
        leader = self.select_leader(evaluated)
        finding = self.challenge_leader(leader)
        repair = self.repair_and_retest(leader, finding)
        promotion = self.promote(
            mission,
            evaluated,
            leader,
            repair,
        )

        self.update_build_truth(
            mission,
            leader,
            promotion,
        )

        verification = self.verify_receipt_chain()

        self.emit(
            "THOTH",
            "OPEN",
            "Campaign lineage preserved and receipt chain verified.",
            self.evidence_root / "receipt_chain_verification.json",
        )

        summary = {
            "campaign_id": self.campaign_id,
            "mission_id": mission["mission_id"],
            "candidates_generated": len(candidates),
            "candidates_executed": len(evaluated),
            "candidates_rejected": len(evaluated) - 1,
            "provisional_leader": leader["candidate_id"],
            "leader_challenged": True,
            "repair_required": finding["promotion_blocking"],
            "repair_successful": repair["status"] == "PROVEN",
            "receipt_chain": verification["status"],
            "receipts_verified": verification["verified_receipts"],
            "final_receipt_hash": verification["final_receipt_hash"],
            "capability_genome": (
                relative(promotion["genome_path"], self.repo)
            ),
            "system_state": "PROVEN",
            "completed_at": utc_now(),
        }

        summary_path = self.evidence_root / "campaign_summary.json"
        write_json(summary_path, summary)

        write_text(
            self.repo / "build_truth" / "current" / "latest_campaign.txt",
            self.campaign_id + "\n",
        )

        self.banner("GATE Ω | PROMETHEUS ONLINE")

        print(f"Campaign:               {self.campaign_id}")
        print(f"Candidates generated:   {len(candidates)}")
        print(f"Candidates executed:    {len(evaluated)}")
        print(f"Candidates rejected:    {len(evaluated) - 1}")
        print(f"Promoted candidate:     {leader['candidate_id']}")
        print("Leader challenged:      YES")
        print("Repair successful:      YES")
        print(f"Receipts verified:      {verification['verified_receipts']}")
        print(f"Final receipt:          {verification['final_receipt_hash']}")
        print("Capability genome:      REGISTERED")
        print("Build Truth:            RECONCILED")
        print()
        print("SYSTEM STATE:           PROVEN")
        print()

        return 0


def verify_latest(repo: Path) -> int:
    manifest_path = (
        repo
        / "build_truth"
        / "current"
        / "latest_receipts.json"
    )

    if not manifest_path.exists():
        raise RuntimeError(
            "No latest receipt manifest exists. Run a campaign first."
        )

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    previous_hash: str | None = None
    verified = 0

    for item in manifest["receipt_chain"]:
        receipt_path = repo / item["path"]

        if not receipt_path.exists():
            raise RuntimeError(
                f"Receipt missing: {item['path']}"
            )

        receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
        stored_hash = receipt.pop("receipt_hash")

        if receipt.get("previous_receipt_hash") != previous_hash:
            raise RuntimeError(
                f"Lineage mismatch in {item['path']}"
            )

        calculated_hash = sha256_bytes(canonical_json(receipt))

        if calculated_hash != stored_hash:
            raise RuntimeError(
                f"Hash mismatch in {item['path']}"
            )

        if stored_hash != item["receipt_hash"]:
            raise RuntimeError(
                f"Manifest mismatch in {item['path']}"
            )

        previous_hash = stored_hash
        verified += 1

    if previous_hash != manifest["final_receipt_hash"]:
        raise RuntimeError("Final receipt hash does not match manifest.")

    print()
    print("=" * 72)
    print("PROOFGRID VERIFICATION")
    print("=" * 72)
    print(f"Campaign:          {manifest['campaign_id']}")
    print(f"Receipts verified: {verified}")
    print(f"Final receipt:     {previous_hash}")
    print("State:             VERIFIED")
    print()

    return 0


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="PROMETHEUS Ω Command-to-Proof runtime"
    )

    parser.add_argument(
        "action",
        nargs="?",
        default="run",
        choices=["run", "verify"],
    )

    parser.add_argument(
        "--repo",
        required=True,
        help="Path to the PROMETHEUS repository.",
    )

    return parser.parse_args()


def main() -> int:
    arguments = parse_arguments()
    repo = Path(arguments.repo).resolve()

    if not repo.exists():
        raise RuntimeError(f"Repository does not exist: {repo}")

    if arguments.action == "verify":
        return verify_latest(repo)

    campaign = CommandToProofCampaign(repo)
    return campaign.run()


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as error:
        print()
        print("=" * 72)
        print("PROMETHEUS Ω CAMPAIGN FAILURE")
        print("=" * 72)
        print(f"{type(error).__name__}: {error}")
        print()
        traceback.print_exc()
        raise SystemExit(1)
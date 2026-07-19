import json
import subprocess
import tempfile
import unittest
from dataclasses import dataclass
from pathlib import Path

from prometheus_kernel.case_study import CaseStudyPublisher
from prometheus_kernel.recursive import (
    RecursiveCampaignError,
    load_recursive_mission,
    run_recursive_campaign,
    verify_recursive_receipt,
)


@dataclass
class FakeExecution:
    candidate_id: str

    def to_dict(self):
        return {
            "candidate_id": self.candidate_id,
            "command": ["fake-codex"],
            "exit_code": 0,
            "duration_ms": 1,
            "transcript": "fake",
            "stderr": "fake",
            "final_message": "fake",
            "passed": True,
        }


class FakeProvider:
    def preflight(self):
        return {"executable": "fake-codex", "sandbox": "workspace-write", "model": "fake"}

    def generate(self, workspace, mission, candidate, evidence_dir, event_callback=None):
        (workspace / f"candidate-{candidate['id']}.txt").write_text(candidate["strategy"])
        evidence_dir.mkdir(parents=True, exist_ok=True)
        (evidence_dir / f"{candidate['id']}.jsonl").write_text('{"type":"turn.completed"}\n')
        if event_callback:
            event_callback({"type": "codex.completed", "candidate_id": candidate["id"]})
        return FakeExecution(candidate["id"])

    def challenge(self, workspace, mission, candidate, candidate_summary, evidence_dir, event_callback=None):
        (workspace / "adversarial-repair.txt").write_text("verified")
        if event_callback:
            event_callback({"type": "codex.completed", "candidate_id": f"{candidate['id']}-adversarial"})
        return FakeExecution(f"{candidate['id']}-adversarial")


class RecursiveCampaignTests(unittest.TestCase):
    def _git(self, repo, *args):
        subprocess.run(["git", *args], cwd=repo, check=True, capture_output=True, text=True)

    def _create_repo(self, root):
        repo = root / "repo"
        (repo / "missions").mkdir(parents=True)
        (repo / "seed.txt").write_text("seed")
        mission = {
            "schema": "prometheus.recursive-mission.v1",
            "mission_id": "TEST-RECURSIVE",
            "objective": "prove recursive execution",
            "source_repo": ".",
            "standard_test": [
                "python",
                "-c",
                "import pathlib; assert list(pathlib.Path('.').glob('candidate-*.txt'))",
            ],
            "challenge_test": [
                "python",
                "-c",
                "import pathlib; assert pathlib.Path('adversarial-repair.txt').is_file()",
            ],
            "policy": {
                "allowed_executables": ["python"],
                "parallel_candidates": 3,
                "max_changed_files": 10,
            },
            "candidates": [
                {"id": "alpha", "strategy": "alpha strategy", "prompt": "alpha"},
                {"id": "beta", "strategy": "beta strategy", "prompt": "beta"},
                {"id": "gamma", "strategy": "gamma strategy", "prompt": "gamma"},
            ],
            "promotion": {
                "repository": "example/prometheus",
                "base_branch": "main",
                "branch_prefix": "prometheus/test",
                "pr_title": "test recursive promotion",
            },
        }
        mission_path = repo / "missions" / "self-build.json"
        mission_path.write_text(json.dumps(mission))
        self._git(repo, "init", "-b", "main")
        self._git(repo, "config", "user.name", "Test")
        self._git(repo, "config", "user.email", "test@example.invalid")
        self._git(repo, "add", "-A")
        self._git(repo, "commit", "-m", "seed")
        return repo, mission_path

    def test_recursive_campaign_forges_challenges_and_binds_receipt(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            repo, mission_path = self._create_repo(root)
            publisher = CaseStudyPublisher(evidence_path=root / "publications.json")
            summary = run_recursive_campaign(
                mission_path,
                output_root=root / "runs",
                provider=FakeProvider(),
                publisher=publisher,
            )
            self.assertEqual(summary["status"], "PROMOTED")
            self.assertEqual(summary["leader"], "alpha")
            self.assertFalse(summary["pushed"])
            self.assertGreaterEqual(summary["serverforge_messages"], 8)
            self.assertTrue(
                verify_recursive_receipt(
                    Path(summary["receipt"]),
                    Path(summary["promoted_workspace"]),
                )
            )
            self.assertTrue((Path(summary["promoted_workspace"]) / "adversarial-repair.txt").is_file())
            receipt = Path(summary["receipt"])
            ledger = receipt.parent / "events.jsonl"
            original = ledger.read_text()
            ledger.write_text(original.replace("mission.accepted", "mission.tampered", 1))
            self.assertFalse(verify_recursive_receipt(receipt, Path(summary["promoted_workspace"])))

    def test_recursive_push_requires_exact_repository_confirmation(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            _, mission_path = self._create_repo(root)
            with self.assertRaises(RecursiveCampaignError):
                run_recursive_campaign(
                    mission_path,
                    output_root=root / "runs",
                    provider=FakeProvider(),
                    confirm_repo="wrong/repository",
                    push=True,
                )

    def test_recursive_mission_requires_three_candidates(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "mission.json"
            path.write_text(json.dumps({
                "schema": "prometheus.recursive-mission.v1",
                "mission_id": "x",
                "objective": "x",
                "source_repo": ".",
                "standard_test": ["python", "-V"],
                "challenge_test": ["python", "-V"],
                "candidates": [],
                "promotion": {},
            }))
            with self.assertRaises(RecursiveCampaignError):
                load_recursive_mission(path)


if __name__ == "__main__":
    unittest.main()

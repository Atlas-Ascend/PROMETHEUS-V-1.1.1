import json
import tempfile
import unittest
from pathlib import Path

from prometheus_kernel.engine import MissionError, execute_mission, load_mission, verify_receipt


class EngineTests(unittest.TestCase):
    def test_mission_requires_three_candidates(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "mission.json"
            path.write_text(json.dumps({
                "mission_id": "x",
                "objective": "x",
                "seed_path": "x",
                "standard_test": ["true"],
                "challenge_test": ["true"],
                "candidates": []
            }))
            with self.assertRaises(MissionError):
                load_mission(path)

    def test_receipt_verification_detects_tampering(self):
        with tempfile.TemporaryDirectory() as directory:
            project = Path(directory)
            (project / "missions").mkdir()
            seed = project / "examples" / "seed"
            seed.mkdir(parents=True)
            (seed / "value.txt").write_text("seed")
            (seed / "test_ok.py").write_text("import unittest\n\nclass T(unittest.TestCase):\n    def test_ok(self): self.assertTrue(True)\n")
            candidates = []
            for index in range(3):
                candidates.append({
                    "id": f"c{index}",
                    "strategy": f"strategy {index}",
                    "operations": [{"type": "write", "path": "value.txt", "content": str(index)}],
                    "repair_operations": []
                })
            mission = {
                "mission_id": "TEST",
                "objective": "prove engine",
                "seed_path": "examples/seed",
                "standard_test": ["python", "-m", "unittest", "test_ok.py"],
                "challenge_test": ["python", "-m", "unittest", "test_ok.py"],
                "candidates": candidates
            }
            mission_path = project / "missions" / "test.json"
            mission_path.write_text(json.dumps(mission))
            summary = execute_mission(mission_path, project / "runs")
            receipt = Path(summary["receipt"])
            self.assertTrue(verify_receipt(receipt))
            promoted_value = Path(summary["promoted_workspace"]) / "value.txt"
            promoted_value.write_text("tampered artifact")
            self.assertFalse(verify_receipt(receipt))
            promoted_value.write_text("0")
            self.assertTrue(verify_receipt(receipt))
            data = json.loads(receipt.read_text())
            leader = next(item for item in data["candidate_results"] if item["candidate_id"] == data["leader"])
            self.assertEqual(len(leader["challenge_attempts"]), 1)
            data["leader"] = "tampered"
            receipt.write_text(json.dumps(data))
            self.assertFalse(verify_receipt(receipt))


if __name__ == "__main__":
    unittest.main()

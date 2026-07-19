import json
import tempfile
import unittest
from pathlib import Path

from prometheus_kernel.ledger import EventLedger, verify_ledger


class LedgerTests(unittest.TestCase):
    def test_chain_verifies_and_tampering_fails(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "events.jsonl"
            ledger = EventLedger(path)
            ledger.append("mission.accepted", {"mission_id": "test"})
            ledger.append("candidate.promoted", {"candidate_id": "a"})
            self.assertTrue(verify_ledger(path))
            lines = path.read_text().splitlines()
            event = json.loads(lines[0])
            event["data"]["mission_id"] = "tampered"
            lines[0] = json.dumps(event)
            path.write_text("\n".join(lines) + "\n")
            self.assertFalse(verify_ledger(path))


if __name__ == "__main__":
    unittest.main()

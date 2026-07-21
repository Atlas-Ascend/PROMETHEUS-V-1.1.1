import tempfile
import unittest
from pathlib import Path

from prometheus_kernel.case_study import CaseStudyPublisher, EVENT_CHANNELS


class FakeDiscordClient:
    def __init__(self):
        self.sent = []

    def snapshot(self, guild_id):
        names = sorted(set(EVENT_CHANNELS.values()))
        return {
            "channels": [
                {"id": f"channel-{index}", "name": name, "type": 0}
                for index, name in enumerate(names)
            ]
        }

    def request(self, method, path, payload=None, reason=None):
        self.sent.append({"method": method, "path": path, "payload": payload, "reason": reason})
        return {"id": f"message-{len(self.sent)}"}


class CaseStudyPublisherTests(unittest.TestCase):
    def test_live_event_routes_to_canonical_channel_and_records_message(self):
        with tempfile.TemporaryDirectory() as directory:
            client = FakeDiscordClient()
            evidence = Path(directory) / "publications.json"
            publisher = CaseStudyPublisher(client, "guild", evidence)
            self.assertEqual(publisher.preflight()["status"], "CONNECTED")
            record = publisher.publish(
                {"type": "candidate.completed", "candidate_id": "alpha", "passed": True}
            )
            self.assertEqual(record["channel"], "candidate-forge")
            self.assertEqual(record["message_id"], "message-1")
            self.assertTrue(evidence.is_file())
            self.assertEqual(client.sent[0]["method"], "POST")


if __name__ == "__main__":
    unittest.main()

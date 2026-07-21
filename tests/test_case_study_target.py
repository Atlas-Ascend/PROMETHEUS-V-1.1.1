import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class CaseStudyTargetTests(unittest.TestCase):
    def setUp(self):
        self.target = json.loads((ROOT / "serverforge/case-study-target.json").read_text(encoding="utf-8"))
        self.topology = json.loads((ROOT / self.target["topology"]).read_text(encoding="utf-8"))
        self.publication = json.loads((ROOT / self.target["baseline_publication"]).read_text(encoding="utf-8"))

    def test_authorized_target_is_pinned(self):
        self.assertEqual(self.target["guild_id"], "1528216351636984036")
        self.assertEqual(self.target["application_id"], "1528218267540263065")
        self.assertEqual(
            self.target["public_key"],
            "72810a56ad400a69f597ec0b62bf816324421351cc612fc1b822c58a323bed75",
        )
        self.assertEqual(self.target["expected_guild_name"], self.topology["guild"]["name"])

    def test_all_case_study_channels_exist_in_topology(self):
        actual = {
            channel["name"]
            for category in self.topology["categories"]
            for channel in category.get("channels", [])
        }
        required = set(self.target["required_public_channels"]) | set(self.target["required_private_channels"])
        self.assertEqual(required - actual, set())

    def test_baseline_publication_targets_existing_channels(self):
        actual = {
            channel["name"]
            for category in self.topology["categories"]
            for channel in category.get("channels", [])
        }
        self.assertEqual(set(self.publication["messages"]) - actual, set())
        self.assertEqual(set(self.publication["pin_channels"]) - actual, set())

    def test_bot_token_is_not_embedded_in_target(self):
        serialized = json.dumps(self.target).upper()
        self.assertNotIn("DISCORD_BOT_TOKEN=", serialized)
        self.assertNotIn("MT", self.target.get("public_key", ""))


if __name__ == "__main__":
    unittest.main()

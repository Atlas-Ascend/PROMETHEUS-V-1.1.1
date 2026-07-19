import json
import tempfile
import unittest
from pathlib import Path

from prometheus_kernel.serverforge import build_plan, empty_snapshot, install_url, load_topology, verify_topology


class ServerForgeTests(unittest.TestCase):
    def topology(self):
        return {
            "schema": "serverforge.topology.v1",
            "guild": {"name": "Forge"},
            "roles": [{"name": "Operator"}],
            "categories": [{
                "name": "CONTROL",
                "access": "private",
                "read_roles": ["Operator"],
                "write_roles": ["Operator"],
                "channels": [{"name": "missions", "type": "text"}]
            }]
        }

    def test_empty_server_plan_is_full_provision(self):
        actions = build_plan(self.topology(), empty_snapshot())
        self.assertEqual([item["action"] for item in actions], [
            "update_guild", "create_role", "create_category", "create_channel"
        ])

    def test_verify_complete_snapshot(self):
        snapshot = {
            "guild": {"id": "1", "name": "Forge"},
            "roles": [{"id": "2", "name": "Operator"}],
            "channels": [
                {"id": "3", "name": "CONTROL", "type": 4, "parent_id": None},
                {"id": "4", "name": "missions", "type": 0, "parent_id": "3"}
            ]
        }
        self.assertTrue(verify_topology(self.topology(), snapshot)["valid"])

    def test_install_url_is_pinned_to_guild(self):
        url = install_url("123", "456")
        self.assertIn("client_id=123", url)
        self.assertIn("guild_id=456", url)
        self.assertIn("disable_guild_select=true", url)

    def test_topology_rejects_unknown_role(self):
        topology = self.topology()
        topology["categories"][0]["read_roles"] = ["Unknown"]
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "topology.json"
            path.write_text(json.dumps(topology))
            with self.assertRaises(Exception):
                load_topology(path)


if __name__ == "__main__":
    unittest.main()

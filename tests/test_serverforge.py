import json
import tempfile
import unittest
from pathlib import Path

from prometheus_kernel.serverforge import (
    SEND_MESSAGES,
    VIEW_CHANNEL,
    _overwrites,
    build_plan,
    empty_snapshot,
    install_url,
    load_topology,
    run_campaign,
    verify_topology,
)


class FakeDiscordClient:
    def __init__(self):
        self.guild = {"id": "guild", "name": "Empty", "features": []}
        self.roles = [{"id": "guild", "name": "@everyone", "managed": False}]
        self.channels = []
        self.messages = 0
        self.blocked_channel_ids = set()

    def preflight(self, guild_id):
        return {
            "bot": {"id": "bot", "username": "ServerForge"},
            "guild": {"id": guild_id, "name": self.guild["name"], "owner_id": "owner"},
        }

    def snapshot(self, guild_id):
        return json.loads(json.dumps({
            "captured_at": "test",
            "guild": self.guild,
            "roles": self.roles,
            "channels": self.channels,
        }))

    def request(self, method, path, payload=None, reason=None):
        if method == "GET" and path == "/users/@me":
            return {"id": "bot", "username": "ServerForge"}
        if method == "PATCH" and path == "/guilds/guild":
            self.guild.update(payload)
            return self.guild
        if method == "POST" and path == "/guilds/guild/roles":
            role = {"id": f"role-{len(self.roles)}", "managed": False, **payload}
            self.roles.append(role)
            return role
        if method == "POST" and path == "/guilds/guild/channels":
            channel = {"id": f"channel-{len(self.channels)}", "position": len(self.channels), **payload}
            self.channels.append(channel)
            return channel
        if method == "PATCH" and path.startswith("/channels/"):
            channel_id = path.rsplit("/", 1)[-1]
            if channel_id in self.blocked_channel_ids:
                from prometheus_kernel.serverforge import ServerForgeError
                raise ServerForgeError(
                    f'Discord API PATCH {path} failed: HTTP 403: {{"message": "Missing Access", "code": 50001}}'
                )
            channel = next(item for item in self.channels if item["id"] == channel_id)
            channel.update(payload)
            return channel
        if method == "POST" and path.endswith("/messages"):
            self.messages += 1
            return {"id": f"message-{self.messages}"}
        raise AssertionError(f"unexpected fake Discord request: {method} {path}")


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

    def test_private_topology_explicitly_allows_bot_identity(self):
        category = self.topology()["categories"][0]
        overwrites = _overwrites("guild", category, {"Operator": "role"}, "bot")
        bot = next(item for item in overwrites if item["id"] == "bot")
        self.assertEqual(bot["type"], 1)
        self.assertTrue(int(bot["allow"]) & VIEW_CHANNEL)
        self.assertTrue(int(bot["allow"]) & SEND_MESSAGES)

    def test_topology_rejects_unknown_role(self):
        topology = self.topology()
        topology["categories"][0]["read_roles"] = ["Unknown"]
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "topology.json"
            path.write_text(json.dumps(topology))
            with self.assertRaises(Exception):
                load_topology(path)

    def test_full_hydra_campaign_reconciles_verifies_and_publishes(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            topology = self.topology()
            topology["categories"][0]["channels"].extend([
                {"name": "live-case-study", "type": "text"},
                {"name": "bridge-control", "type": "text"},
                {"name": "promotion-receipts", "type": "text"},
            ])
            topology_path = root / "topology.json"
            topology_path.write_text(json.dumps(topology))
            result = run_campaign(
                FakeDiscordClient(),
                "guild",
                topology,
                topology_path,
                root / "evidence",
            )
            self.assertEqual(result["status"], "LIVE_VERIFIED")
            self.assertTrue(all(head["passed"] for head in result["hydra_heads"]))
            self.assertEqual(len(result["publications"]), 3)
            self.assertTrue((Path(result["evidence_root"]) / "campaign-receipt.json").is_file())

    def test_hydra_recovers_an_inaccessible_legacy_category(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            topology = self.topology()
            topology["categories"][0]["channels"].extend([
                {"name": "live-case-study", "type": "text"},
                {"name": "bridge-control", "type": "text"},
                {"name": "promotion-receipts", "type": "text"},
            ])
            topology_path = root / "topology.json"
            topology_path.write_text(json.dumps(topology))
            client = FakeDiscordClient()
            client.channels.append({
                "id": "locked-category",
                "name": "CONTROL",
                "type": 4,
                "parent_id": None,
                "permission_overwrites": [],
            })
            client.blocked_channel_ids.add("locked-category")
            result = run_campaign(client, "guild", topology, topology_path, root / "evidence")
            self.assertEqual(result["status"], "LIVE_VERIFIED")
            receipt = json.loads((Path(result["evidence_root"]) / "campaign-receipt.json").read_text())
            self.assertEqual(receipt["recoveries"][0]["orphan_id"], "locked-category")
            self.assertNotEqual(receipt["recoveries"][0]["replacement_id"], "locked-category")


if __name__ == "__main__":
    unittest.main()

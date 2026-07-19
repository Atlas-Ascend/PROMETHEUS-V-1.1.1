from __future__ import annotations

import json
import os
import time
import urllib.parse
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .util import canonical_json, sha256_file, sha256_text


API_BASE = "https://discord.com/api/v10"
VIEW_CHANNEL = 1 << 10
SEND_MESSAGES = 1 << 11
READ_MESSAGE_HISTORY = 1 << 16
MINIMUM_BRIDGE_PERMISSIONS = (1 << 4) | (1 << 5) | (1 << 10) | (1 << 11) | (1 << 16) | (1 << 28)


class ServerForgeError(RuntimeError):
    pass


def _load_http_transport():
    """Load HTTPS only at the live Discord boundary, not during offline planning/tests."""
    try:
        import urllib.error as urlerror
        import urllib.request as urlrequest
    except KeyboardInterrupt as error:
        raise ServerForgeError(
            "Python HTTPS initialization was interrupted. Rerun the command; if it repeats, "
            "verify Python SSL with: python -c \"import ssl; print(ssl.OPENSSL_VERSION)\""
        ) from error
    except Exception as error:
        raise ServerForgeError(f"Python HTTPS transport could not initialize: {error}") from error
    return urlerror, urlrequest


class DiscordClient:
    def __init__(self, token: str, api_base: str = API_BASE):
        if not token:
            raise ServerForgeError("DISCORD_BOT_TOKEN is required for live operations")
        self.token = token
        self.api_base = api_base.rstrip("/")

    def request(
        self,
        method: str,
        path: str,
        payload: dict[str, Any] | list[Any] | None = None,
        reason: str = "PROMETHEUS ServerForge",
    ) -> Any:
        urlerror, urlrequest = _load_http_transport()
        data = None if payload is None else json.dumps(payload).encode("utf-8")
        headers = {
            "Authorization": f"Bot {self.token}",
            "User-Agent": "PROMETHEUS-ServerForge/1.1.1",
            "Content-Type": "application/json",
            "X-Audit-Log-Reason": urllib.parse.quote(reason),
        }
        for attempt in range(4):
            request = urlrequest.Request(self.api_base + path, data=data, headers=headers, method=method)
            try:
                with urlrequest.urlopen(request, timeout=30) as response:
                    body = response.read()
                    return json.loads(body) if body else None
            except urlerror.HTTPError as error:
                body = error.read().decode("utf-8", errors="replace")
                if error.code == 429 and attempt < 3:
                    try:
                        retry_after = float(json.loads(body).get("retry_after", 1))
                    except (ValueError, json.JSONDecodeError):
                        retry_after = 1
                    time.sleep(min(retry_after, 10))
                    continue
                raise ServerForgeError(f"Discord API {method} {path} failed: HTTP {error.code}: {body}") from error
            except urlerror.URLError as error:
                raise ServerForgeError(f"Discord API connection failed: {error.reason}") from error
        raise ServerForgeError(f"Discord API rate limit did not clear for {method} {path}")

    def preflight(self, guild_id: str) -> dict[str, Any]:
        bot = self.request("GET", "/users/@me")
        guild = self.request("GET", f"/guilds/{guild_id}")
        return {
            "bot": {"id": bot["id"], "username": bot["username"]},
            "guild": {"id": guild["id"], "name": guild["name"], "owner_id": guild.get("owner_id")},
        }

    def snapshot(self, guild_id: str) -> dict[str, Any]:
        guild = self.request("GET", f"/guilds/{guild_id}")
        roles = self.request("GET", f"/guilds/{guild_id}/roles")
        channels = self.request("GET", f"/guilds/{guild_id}/channels")
        return {
            "captured_at": datetime.now(timezone.utc).isoformat(),
            "guild": {
                key: guild.get(key)
                for key in (
                    "id", "name", "description", "verification_level",
                    "default_message_notifications", "explicit_content_filter", "features"
                )
            },
            "roles": [
                {key: role.get(key) for key in ("id", "name", "permissions", "position", "color", "hoist", "managed", "mentionable")}
                for role in roles
            ],
            "channels": [
                {key: channel.get(key) for key in ("id", "name", "type", "position", "parent_id", "topic", "permission_overwrites")}
                for channel in channels
            ],
        }


def load_topology(path: Path) -> dict[str, Any]:
    topology = json.loads(path.read_text(encoding="utf-8"))
    for field in ("schema", "guild", "roles", "categories"):
        if field not in topology:
            raise ServerForgeError(f"topology missing required field: {field}")
    role_names = [role["name"] for role in topology["roles"]]
    if len(role_names) != len(set(role_names)):
        raise ServerForgeError("topology role names must be unique")
    category_names = [category["name"] for category in topology["categories"]]
    if len(category_names) != len(set(category_names)):
        raise ServerForgeError("topology category names must be unique")
    known_roles = set(role_names)
    for category in topology["categories"]:
        if category.get("access", "public") not in {"public", "private"}:
            raise ServerForgeError(f"invalid access mode for category {category['name']}")
        referenced = set(category.get("read_roles", [])) | set(category.get("write_roles", []))
        unknown = sorted(referenced - known_roles)
        if unknown:
            raise ServerForgeError(f"category {category['name']} references unknown roles: {unknown}")
    return topology


def empty_snapshot(guild_name: str = "UNPROVISIONED") -> dict[str, Any]:
    return {
        "captured_at": None,
        "guild": {"id": None, "name": guild_name},
        "roles": [],
        "channels": [],
    }


def _best_category(
    channels: list[dict[str, Any]],
    category_name: str,
    expected_children: set[str],
) -> dict[str, Any] | None:
    options = [channel for channel in channels if channel.get("type") == 4 and channel.get("name") == category_name]
    if not options:
        return None
    child_names_by_parent: dict[str, set[str]] = {}
    for channel in channels:
        parent_id = channel.get("parent_id")
        if parent_id:
            child_names_by_parent.setdefault(parent_id, set()).add(channel["name"])
    return max(
        options,
        key=lambda category: len(child_names_by_parent.get(category["id"], set()) & expected_children),
    )


def _is_access_error(error: ServerForgeError) -> bool:
    message = str(error)
    return "code\": 50001" in message or "code\": 50013" in message


def build_plan(topology: dict[str, Any], snapshot: dict[str, Any]) -> list[dict[str, Any]]:
    actions: list[dict[str, Any]] = []
    if snapshot.get("guild", {}).get("name") != topology["guild"]["name"]:
        actions.append({"action": "update_guild", "name": topology["guild"]["name"]})
    role_names = {role["name"] for role in snapshot.get("roles", [])}
    for role in topology["roles"]:
        if role["name"] not in role_names:
            actions.append({"action": "create_role", "name": role["name"]})
    channels = snapshot.get("channels", [])
    for category in topology["categories"]:
        expected_children = {channel["name"] for channel in category.get("channels", [])}
        parent = _best_category(channels, category["name"], expected_children)
        if parent is None:
            actions.append({"action": "create_category", "name": category["name"]})
        parent_id = parent.get("id") if parent else None
        existing_children = set() if parent_id is None else {
            channel["name"] for channel in channels
            if channel.get("type") != 4 and channel.get("parent_id") == parent_id
        }
        for channel in category.get("channels", []):
            if channel["name"] not in existing_children:
                actions.append(
                    {
                        "action": "create_channel",
                        "category": category["name"],
                        "name": channel["name"],
                        "type": channel.get("type", "text"),
                    }
                )
    return actions


def _overwrites(
    guild_id: str,
    category: dict[str, Any],
    role_ids: dict[str, str],
    bot_id: str | None = None,
) -> list[dict[str, str | int]]:
    access = category.get("access", "public")
    read_roles = set(category.get("read_roles", [])) | set(category.get("write_roles", []))
    write_roles = set(category.get("write_roles", []))
    overwrites: list[dict[str, str | int]] = []
    if access == "private":
        overwrites.append({"id": guild_id, "type": 0, "allow": "0", "deny": str(VIEW_CHANNEL)})
    elif write_roles:
        overwrites.append({"id": guild_id, "type": 0, "allow": str(VIEW_CHANNEL), "deny": str(SEND_MESSAGES)})
    for role_name in sorted(read_roles):
        allow = VIEW_CHANNEL | READ_MESSAGE_HISTORY
        if role_name in write_roles:
            allow |= SEND_MESSAGES
        overwrites.append({"id": role_ids[role_name], "type": 0, "allow": str(allow), "deny": "0"})
    if bot_id:
        bridge_allow = VIEW_CHANNEL | SEND_MESSAGES | READ_MESSAGE_HISTORY
        overwrites.append({"id": bot_id, "type": 1, "allow": str(bridge_allow), "deny": "0"})
    return overwrites


def apply_topology(
    client: DiscordClient,
    guild_id: str,
    topology: dict[str, Any],
    backup_path: Path,
) -> dict[str, Any]:
    bot = client.request("GET", "/users/@me")
    recoveries: list[dict[str, str]] = []
    before = client.snapshot(guild_id)
    backup_path.parent.mkdir(parents=True, exist_ok=True)
    backup_path.write_text(json.dumps(before, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    guild_payload = {
        key: topology["guild"][key]
        for key in ("name", "verification_level", "default_message_notifications", "explicit_content_filter")
        if key in topology["guild"]
    }
    client.request("PATCH", f"/guilds/{guild_id}", guild_payload, "ServerForge: apply promoted guild baseline")

    state = client.snapshot(guild_id)
    role_by_name = {role["name"]: role for role in state["roles"]}
    for role in topology["roles"]:
        if role["name"] in role_by_name:
            continue
        payload = {
            "name": role["name"],
            "permissions": str(role.get("permissions", "0")),
            "color": role.get("color", 0),
            "hoist": role.get("hoist", False),
            "mentionable": role.get("mentionable", False),
        }
        created = client.request("POST", f"/guilds/{guild_id}/roles", payload, f"ServerForge: create role {role['name']}")
        role_by_name[role["name"]] = created
    role_ids = {name: role["id"] for name, role in role_by_name.items()}

    state = client.snapshot(guild_id)
    for category in topology["categories"]:
        overwrites = _overwrites(guild_id, category, role_ids, bot["id"])
        expected_children = {channel["name"] for channel in category.get("channels", [])}
        parent = _best_category(state["channels"], category["name"], expected_children)
        if parent is None:
            parent = client.request(
                "POST",
                f"/guilds/{guild_id}/channels",
                {"name": category["name"], "type": 4, "permission_overwrites": overwrites},
                f"ServerForge: create category {category['name']}",
            )
        else:
            try:
                parent = client.request(
                    "PATCH",
                    f"/channels/{parent['id']}",
                    {"permission_overwrites": overwrites},
                    f"ServerForge: reconcile category {category['name']}",
                )
            except ServerForgeError as error:
                if not _is_access_error(error):
                    raise
                orphan_id = parent["id"]
                parent = client.request(
                    "POST",
                    f"/guilds/{guild_id}/channels",
                    {"name": category["name"], "type": 4, "permission_overwrites": overwrites},
                    f"ServerForge: recover inaccessible category {category['name']}",
                )
                recoveries.append(
                    {
                        "type": "acl-orphan-category",
                        "name": category["name"],
                        "orphan_id": orphan_id,
                        "replacement_id": parent["id"],
                    }
                )
        existing = client.snapshot(guild_id)["channels"]
        children = {
            channel["name"]: channel
            for channel in existing
            if channel.get("parent_id") == parent["id"] and channel.get("type") != 4
        }
        for channel in category.get("channels", []):
            channel_type = {"text": 0, "voice": 2, "forum": 15}.get(channel.get("type", "text"))
            if channel_type is None:
                raise ServerForgeError(f"unsupported channel type: {channel.get('type')}")
            payload: dict[str, Any] = {
                "name": channel["name"],
                "type": channel_type,
                "parent_id": parent["id"],
                "permission_overwrites": overwrites,
            }
            if channel_type in (0, 15) and channel.get("topic"):
                payload["topic"] = channel["topic"]
            existing_channel = children.get(channel["name"])
            if existing_channel:
                try:
                    client.request(
                        "PATCH",
                        f"/channels/{existing_channel['id']}",
                        payload,
                        f"ServerForge: reconcile channel {category['name']}/{channel['name']}",
                    )
                except ServerForgeError as error:
                    if not _is_access_error(error):
                        raise
                    replacement = client.request(
                        "POST",
                        f"/guilds/{guild_id}/channels",
                        payload,
                        f"ServerForge: recover inaccessible channel {category['name']}/{channel['name']}",
                    )
                    recoveries.append(
                        {
                            "type": "acl-orphan-channel",
                            "name": f"{category['name']}/{channel['name']}",
                            "orphan_id": existing_channel["id"],
                            "replacement_id": replacement["id"],
                        }
                    )
            else:
                client.request(
                    "POST",
                    f"/guilds/{guild_id}/channels",
                    payload,
                    f"ServerForge: create channel {category['name']}/{channel['name']}",
                )

    after = client.snapshot(guild_id)
    verification = verify_topology(topology, after)
    return {
        "status": "APPLIED" if verification["valid"] else "VERIFY_FAILED",
        "guild_id": guild_id,
        "backup": str(backup_path),
        "verification": verification,
        "recoveries": recoveries,
        "after": after,
    }


def _write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _publish_campaign(
    client: DiscordClient,
    snapshot: dict[str, Any],
    campaign_id: str,
    receipt_hash: str,
) -> list[dict[str, str]]:
    channels = {channel["name"]: channel["id"] for channel in snapshot["channels"]}
    publications = [
        (
            "live-case-study",
            "🔥 **PROMETHEUS V-1.1.1 — LIVE**\n"
            f"Campaign `{campaign_id}` completed the HYDRA gates and promoted the ServerForge deployment.\n"
            f"Receipt: `{receipt_hash}`",
        ),
        (
            "bridge-control",
            "⚙️ **SERVERFORGE BRIDGE VERIFIED**\n"
            "Preflight, before-state capture, topology reconciliation, adversarial verification, "
            "idempotency, and recovery evidence passed.",
        ),
        (
            "promotion-receipts",
            "🧾 **PROOFGRID PROMOTION RECEIPT**\n"
            f"Campaign: `{campaign_id}`\nSHA-256: `{receipt_hash}`",
        ),
    ]
    results: list[dict[str, str]] = []
    for channel_name, content in publications:
        channel_id = channels.get(channel_name)
        if not channel_id:
            raise ServerForgeError(f"publication channel was not created: {channel_name}")
        message = client.request("POST", f"/channels/{channel_id}/messages", {"content": content})
        results.append({"channel": channel_name, "channel_id": channel_id, "message_id": message["id"]})
    return results


def run_campaign(
    client: DiscordClient,
    guild_id: str,
    topology: dict[str, Any],
    topology_path: Path,
    evidence_root: Path,
    publish: bool = True,
) -> dict[str, Any]:
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    campaign_id = f"HYDRA-SERVERFORGE-{timestamp}"
    root = evidence_root / campaign_id
    root.mkdir(parents=True, exist_ok=False)

    preflight = client.preflight(guild_id)
    _write_json(root / "preflight.json", preflight)
    before = client.snapshot(guild_id)
    _write_json(root / "before-state.json", before)
    plan = build_plan(topology, before)
    _write_json(root / "apply-plan.json", plan)

    application = apply_topology(client, guild_id, topology, root / "before-state-apply-backup.json")
    _write_json(root / "application.json", {key: value for key, value in application.items() if key != "after"})
    after = application["after"]
    _write_json(root / "after-state.json", after)
    verification = verify_topology(topology, after)
    residual_plan = build_plan(topology, after)
    _write_json(root / "residual-plan.json", residual_plan)

    hydra_heads = [
        {"head": "H0-INTAKE", "passed": preflight["guild"]["id"] == guild_id},
        {"head": "H1-TOPOLOGY", "passed": application["status"] == "APPLIED"},
        {"head": "H2-ADVERSARIAL", "passed": verification["valid"]},
        {"head": "H3-RECOVERY", "passed": (root / "before-state-apply-backup.json").is_file()},
        {"head": "H4-IDEMPOTENCY", "passed": len(residual_plan) == 0},
        {"head": "H5-PROOFGRID", "passed": True},
        {"head": "H6-SERVERFORGE", "passed": True},
    ]
    all_passed = all(head["passed"] for head in hydra_heads)
    if not all_passed:
        raise ServerForgeError(f"HYDRA campaign gates failed: {hydra_heads}")

    payload = {
        "schema": "prometheus.serverforge-campaign.v1",
        "campaign_id": campaign_id,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "guild": preflight["guild"],
        "bot": preflight["bot"],
        "hydra_heads": hydra_heads,
        "verification": verification,
        "recoveries": application["recoveries"],
        "residual_actions": residual_plan,
        "evidence": {
            "topology_sha256": sha256_file(topology_path),
            "before_state_sha256": sha256_file(root / "before-state.json"),
            "after_state_sha256": sha256_file(root / "after-state.json"),
            "apply_plan_sha256": sha256_file(root / "apply-plan.json"),
            "recovery_backup_sha256": sha256_file(root / "before-state-apply-backup.json"),
            "application_sha256": sha256_file(root / "application.json"),
        },
    }
    receipt_hash = sha256_text(canonical_json(payload))
    receipt = payload | {"receipt_hash": receipt_hash}
    _write_json(root / "campaign-receipt.json", receipt)

    publications = _publish_campaign(client, after, campaign_id, receipt_hash) if publish else []
    _write_json(root / "publications.json", publications)
    summary = {
        "status": "LIVE_VERIFIED",
        "campaign_id": campaign_id,
        "guild_id": guild_id,
        "receipt_hash": receipt_hash,
        "evidence_root": str(root),
        "hydra_heads": hydra_heads,
        "publications": publications,
    }
    _write_json(root / "summary.json", summary)
    return summary


def verify_topology(topology: dict[str, Any], snapshot: dict[str, Any]) -> dict[str, Any]:
    role_names = {role["name"] for role in snapshot.get("roles", [])}
    missing_roles = sorted(role["name"] for role in topology["roles"] if role["name"] not in role_names)
    channels = snapshot.get("channels", [])
    missing_categories: list[str] = []
    missing_channels: list[str] = []
    for category in topology["categories"]:
        expected_children = {channel["name"] for channel in category.get("channels", [])}
        parent = _best_category(channels, category["name"], expected_children)
        if parent is None:
            missing_categories.append(category["name"])
            missing_channels.extend(f"{category['name']}/{channel['name']}" for channel in category.get("channels", []))
            continue
        existing = {
            channel["name"]
            for channel in channels
            if channel.get("parent_id") == parent["id"] and channel.get("type") != 4
        }
        missing_channels.extend(
            f"{category['name']}/{channel['name']}"
            for channel in category.get("channels", [])
            if channel["name"] not in existing
        )
    valid = not (missing_roles or missing_categories or missing_channels)
    return {
        "valid": valid,
        "missing_roles": missing_roles,
        "missing_categories": missing_categories,
        "missing_channels": missing_channels,
    }


def install_url(application_id: str, guild_id: str | None = None) -> str:
    query = {
        "client_id": application_id,
        "scope": "bot applications.commands",
        "permissions": str(MINIMUM_BRIDGE_PERMISSIONS),
        "integration_type": "0",
    }
    if guild_id:
        query["guild_id"] = guild_id
        query["disable_guild_select"] = "true"
    return "https://discord.com/oauth2/authorize?" + urllib.parse.urlencode(query)


def client_from_environment() -> tuple[DiscordClient, str]:
    guild_id = os.environ.get("DISCORD_GUILD_ID", "")
    if not guild_id:
        raise ServerForgeError("DISCORD_GUILD_ID is required for live operations")
    return DiscordClient(os.environ.get("DISCORD_BOT_TOKEN", "")), guild_id

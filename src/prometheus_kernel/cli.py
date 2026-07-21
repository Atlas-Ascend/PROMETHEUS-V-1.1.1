from __future__ import annotations

import argparse
import json
import os
from datetime import datetime, timezone
from pathlib import Path

from .engine import execute_mission, verify_receipt
from .case_study import CaseStudyPublisher
from .recursive import run_recursive_campaign, verify_recursive_receipt
from .serverforge import (
    ServerForgeError,
    apply_topology,
    build_plan,
    client_from_environment,
    empty_snapshot,
    install_url,
    load_topology,
    run_campaign,
    verify_topology,
)


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(prog="prometheus", description="PROMETHEUS mission-to-proof kernel")
    root.add_argument("--version", action="version", version="PROMETHEUS 1.1.1")
    commands = root.add_subparsers(dest="command", required=True)
    run = commands.add_parser("run", help="execute a mission")
    run.add_argument("mission", type=Path)
    run.add_argument("--output-root", type=Path)
    verify = commands.add_parser("verify", help="verify a promotion receipt")
    verify.add_argument("receipt", type=Path)
    recursive = commands.add_parser("recursive", help="run the Codex-backed recursive forge")
    recursive.add_argument("mission", type=Path, nargs="?", default=Path("missions/self-build.json"))
    recursive.add_argument("--output-root", type=Path)
    recursive.add_argument("--confirm-repo")
    recursive.add_argument("--push", action="store_true")
    recursive.add_argument("--open-pr", action="store_true")
    recursive.add_argument("--publish-serverforge", action="store_true")
    recursive_verify = commands.add_parser("verify-recursive", help="verify a recursive promotion receipt")
    recursive_verify.add_argument("receipt", type=Path)
    recursive_verify.add_argument("--workspace", type=Path)
    forge = commands.add_parser("serverforge", help="bridge PROMETHEUS to an authorized Discord server")
    forge_commands = forge.add_subparsers(dest="serverforge_command", required=True)
    install = forge_commands.add_parser("install-url", help="create the pinned Discord bot installation URL")
    install.add_argument("--application-id", default=os.environ.get("DISCORD_APPLICATION_ID"))
    install.add_argument("--guild-id", default=os.environ.get("DISCORD_GUILD_ID"))
    plan = forge_commands.add_parser("plan", help="plan topology changes without mutation")
    plan.add_argument("topology", type=Path, nargs="?", default=Path("serverforge/topology.json"))
    plan.add_argument("--snapshot", type=Path)
    forge_commands.add_parser("preflight", help="verify bot and guild connectivity")
    snapshot = forge_commands.add_parser("snapshot", help="capture a secrets-redacted Discord state")
    snapshot.add_argument("--output", type=Path)
    apply = forge_commands.add_parser("apply", help="apply the topology to the confirmed guild")
    apply.add_argument("topology", type=Path, nargs="?", default=Path("serverforge/topology.json"))
    apply.add_argument("--confirm-guild", required=True)
    apply.add_argument("--backup", type=Path)
    live_verify = forge_commands.add_parser("verify", help="verify live Discord topology")
    live_verify.add_argument("topology", type=Path, nargs="?", default=Path("serverforge/topology.json"))
    campaign = forge_commands.add_parser("campaign", help="run the complete HYDRA ServerForge campaign")
    campaign.add_argument("topology", type=Path, nargs="?", default=Path("serverforge/topology.json"))
    campaign.add_argument("--confirm-guild", required=True)
    campaign.add_argument("--evidence-root", type=Path, default=Path(".prometheus/serverforge/campaigns"))
    campaign.add_argument("--no-publish", action="store_true")
    return root


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    if args.command == "run":
        summary = execute_mission(args.mission, args.output_root)
        print(json.dumps(summary, indent=2, sort_keys=True))
        return 0
    if args.command == "verify":
        valid = verify_receipt(args.receipt)
        print(json.dumps({"receipt": str(args.receipt), "valid": valid}, indent=2))
        return 0 if valid else 1
    if args.command == "verify-recursive":
        valid = verify_recursive_receipt(args.receipt, args.workspace)
        print(json.dumps({"receipt": str(args.receipt), "valid": valid}, indent=2))
        return 0 if valid else 1
    if args.command == "recursive":
        try:
            publisher = None
            if args.publish_serverforge:
                client, guild_id = client_from_environment()
                publisher = CaseStudyPublisher(client, guild_id)
            result = run_recursive_campaign(
                args.mission,
                output_root=args.output_root,
                publisher=publisher,
                confirm_repo=args.confirm_repo,
                push=args.push,
                open_pr=args.open_pr,
            )
            print(json.dumps(result, indent=2, sort_keys=True))
            return 0
        except Exception as error:
            print(json.dumps({"status": "BLOCKED", "error": str(error)}, indent=2))
            return 2
    try:
        if args.serverforge_command == "install-url":
            if not args.application_id:
                raise ServerForgeError("DISCORD_APPLICATION_ID or --application-id is required")
            result = {"install_url": install_url(args.application_id, args.guild_id)}
        elif args.serverforge_command == "plan":
            topology = load_topology(args.topology)
            if args.snapshot:
                state = json.loads(args.snapshot.read_text(encoding="utf-8"))
                source = str(args.snapshot)
            elif os.environ.get("DISCORD_BOT_TOKEN") and os.environ.get("DISCORD_GUILD_ID"):
                client, guild_id = client_from_environment()
                state = client.snapshot(guild_id)
                source = "live"
            else:
                state = empty_snapshot()
                source = "offline-empty-server"
            result = {"status": "PLANNED", "source": source, "actions": build_plan(topology, state)}
        elif args.serverforge_command == "preflight":
            client, guild_id = client_from_environment()
            result = {"status": "CONNECTED", **client.preflight(guild_id)}
        elif args.serverforge_command == "snapshot":
            client, guild_id = client_from_environment()
            state = client.snapshot(guild_id)
            output = args.output or Path(".prometheus/serverforge/backups") / f"{guild_id}-{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}.json"
            output.parent.mkdir(parents=True, exist_ok=True)
            output.write_text(json.dumps(state, indent=2, sort_keys=True) + "\n", encoding="utf-8")
            result = {"status": "SNAPSHOT_CAPTURED", "path": str(output), "guild_id": guild_id}
        elif args.serverforge_command == "apply":
            client, guild_id = client_from_environment()
            if args.confirm_guild != guild_id:
                raise ServerForgeError("--confirm-guild must exactly match DISCORD_GUILD_ID")
            topology = load_topology(args.topology)
            backup = args.backup or Path(".prometheus/serverforge/backups") / f"{guild_id}-{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}.json"
            result = apply_topology(client, guild_id, topology, backup)
        elif args.serverforge_command == "verify":
            client, guild_id = client_from_environment()
            topology = load_topology(args.topology)
            result = verify_topology(topology, client.snapshot(guild_id))
        else:
            client, guild_id = client_from_environment()
            if args.confirm_guild != guild_id:
                raise ServerForgeError("--confirm-guild must exactly match DISCORD_GUILD_ID")
            topology_path = args.topology.resolve()
            topology = load_topology(topology_path)
            result = run_campaign(
                client,
                guild_id,
                topology,
                topology_path,
                args.evidence_root,
                publish=not args.no_publish,
            )
        print(json.dumps(result, indent=2, sort_keys=True))
        return 0 if result.get("valid", True) and result.get("status") != "VERIFY_FAILED" else 1
    except ServerForgeError as error:
        print(json.dumps({"status": "BLOCKED", "error": str(error)}, indent=2))
        return 2

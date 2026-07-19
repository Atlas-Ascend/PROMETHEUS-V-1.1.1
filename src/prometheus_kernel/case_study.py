from __future__ import annotations

import json
import threading
from pathlib import Path
from typing import Any

from .serverforge import DiscordClient


EVENT_CHANNELS = {
    "mission.accepted": "mission-intake",
    "candidate.started": "candidate-forge",
    "candidate.completed": "candidate-forge",
    "candidate.failed": "candidate-forge",
    "leader.selected": "promotion-gate",
    "challenge.started": "challenge-queue",
    "challenge.completed": "findings",
    "repair.completed": "repair-verification",
    "promotion.completed": "promotion-receipts",
    "telemetry": "telemetry",
}


class CaseStudyPublisher:
    """Publishes bounded recursive-campaign telemetry to an authorized ServerForge guild."""

    def __init__(
        self,
        client: DiscordClient | None = None,
        guild_id: str | None = None,
        evidence_path: Path | None = None,
    ):
        self.client = client
        self.guild_id = guild_id
        self.evidence_path = evidence_path
        self.channel_ids: dict[str, str] = {}
        self.publications: list[dict[str, Any]] = []
        self._lock = threading.Lock()

    @property
    def live(self) -> bool:
        return self.client is not None and bool(self.guild_id)

    def preflight(self) -> dict[str, Any]:
        if not self.live:
            return {"status": "OFFLINE", "live": False}
        snapshot = self.client.snapshot(self.guild_id or "")
        self.channel_ids = {
            channel["name"]: channel["id"]
            for channel in snapshot["channels"]
            if channel.get("type") in (0, 5)
        }
        required = sorted(set(EVENT_CHANNELS.values()))
        missing = [name for name in required if name not in self.channel_ids]
        if missing:
            raise RuntimeError(f"ServerForge case-study channels are missing: {missing}")
        return {"status": "CONNECTED", "live": True, "guild_id": self.guild_id}

    def _render(self, event: dict[str, Any]) -> str:
        event_type = event["type"]
        fields = [f"**{key.replace('_', ' ').title()}:** `{value}`" for key, value in event.items() if key != "type"]
        content = f"⚙️ **PROMETHEUS — {event_type.upper()}**\n" + "\n".join(fields)
        return content[:1990]

    def publish(self, event: dict[str, Any]) -> dict[str, Any]:
        event_type = event.get("type", "telemetry")
        channel_name = EVENT_CHANNELS.get(event_type, "telemetry")
        record: dict[str, Any] = {
            "event": json.loads(json.dumps(event, default=str)),
            "channel": channel_name,
            "live": self.live,
        }
        with self._lock:
            if self.live:
                channel_id = self.channel_ids[channel_name]
                message = self.client.request(
                    "POST",
                    f"/channels/{channel_id}/messages",
                    {"content": self._render(event)},
                    f"PROMETHEUS recursive campaign: {event_type}",
                )
                record.update({"channel_id": channel_id, "message_id": message["id"]})
            self.publications.append(record)
            if self.evidence_path:
                self.evidence_path.parent.mkdir(parents=True, exist_ok=True)
                self.evidence_path.write_text(
                    json.dumps(self.publications, indent=2, sort_keys=True) + "\n",
                    encoding="utf-8",
                )
        return record

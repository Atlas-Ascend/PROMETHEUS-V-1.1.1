from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .util import canonical_json, sha256_text


class EventLedger:
    """Append-only, hash-chained event ledger for one mission run."""

    def __init__(self, path: Path):
        self.path = path
        self.index = 0
        self.head = "0" * 64

    def append(self, event_type: str, data: dict[str, Any]) -> dict[str, Any]:
        payload = {
            "index": self.index,
            "type": event_type,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "data": data,
            "previous_hash": self.head,
        }
        event = payload | {"event_hash": sha256_text(canonical_json(payload))}
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(event, sort_keys=True) + "\n")
        self.head = event["event_hash"]
        self.index += 1
        return event


def verify_ledger(path: Path) -> bool:
    previous = "0" * 64
    expected_index = 0
    for line in path.read_text(encoding="utf-8").splitlines():
        event = json.loads(line)
        event_hash = event.pop("event_hash")
        if event.get("index") != expected_index or event.get("previous_hash") != previous:
            return False
        if event_hash != sha256_text(canonical_json(event)):
            return False
        previous = event_hash
        expected_index += 1
    return expected_index > 0

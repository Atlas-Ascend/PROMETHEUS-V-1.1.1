from __future__ import annotations

import shutil
from pathlib import Path
from typing import Any


def safe_target(workspace: Path, relative_path: str) -> Path:
    target = (workspace / relative_path).resolve()
    root = workspace.resolve()
    if target != root and root not in target.parents:
        raise ValueError(f"operation escapes workspace: {relative_path}")
    return target


def apply_operations(workspace: Path, operations: list[dict[str, Any]]) -> None:
    for operation in operations:
        kind = operation.get("type")
        target = safe_target(workspace, operation["path"])
        if kind == "write":
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(operation.get("content", ""), encoding="utf-8")
        elif kind == "replace":
            old = operation["old"]
            source = target.read_text(encoding="utf-8")
            if old not in source:
                raise ValueError(f"replace source not found in {operation['path']}")
            target.write_text(source.replace(old, operation["new"]), encoding="utf-8")
        elif kind == "delete":
            if target.is_dir():
                shutil.rmtree(target)
            elif target.exists():
                target.unlink()
        else:
            raise ValueError(f"unsupported operation type: {kind!r}")

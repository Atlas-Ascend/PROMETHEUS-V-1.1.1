from __future__ import annotations

import hashlib
import json
import os
import subprocess
import time
from pathlib import Path
from typing import Any

from .models import CommandResult


def canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def artifact_manifest(root: Path) -> list[dict[str, Any]]:
    artifacts: list[dict[str, Any]] = []
    for path in sorted(root.rglob("*")):
        if not path.is_file() or ".git" in path.parts:
            continue
        artifacts.append(
            {
                "path": path.relative_to(root).as_posix(),
                "sha256": sha256_file(path),
                "bytes": path.stat().st_size,
            }
        )
    return artifacts


def run_command(
    command: list[str],
    cwd: Path,
    env: dict[str, str] | None = None,
    timeout_seconds: int = 60,
    max_output_chars: int = 100_000,
) -> CommandResult:
    started = time.monotonic()
    try:
        process = subprocess.run(
            command,
            cwd=cwd,
            env=(os.environ | env) if env else None,
            text=True,
            capture_output=True,
            check=False,
            timeout=timeout_seconds,
        )
        exit_code = process.returncode
        stdout = process.stdout[-max_output_chars:]
        stderr = process.stderr[-max_output_chars:]
        timed_out = False
    except subprocess.TimeoutExpired as error:
        captured_stdout = error.stdout.decode("utf-8", errors="replace") if isinstance(error.stdout, bytes) else (error.stdout or "")
        captured_stderr = error.stderr.decode("utf-8", errors="replace") if isinstance(error.stderr, bytes) else (error.stderr or "")
        exit_code = 124
        stdout = captured_stdout[-max_output_chars:]
        stderr = (captured_stderr + f"\ncommand timed out after {timeout_seconds}s")[-max_output_chars:]
        timed_out = True
    return CommandResult(
        command=command,
        exit_code=exit_code,
        stdout=stdout,
        stderr=stderr,
        duration_ms=round((time.monotonic() - started) * 1000),
        timed_out=timed_out,
    )


def require_success(result: CommandResult, context: str) -> None:
    if result.passed:
        return
    raise RuntimeError(
        f"{context} failed with exit code {result.exit_code}\n"
        f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}"
    )

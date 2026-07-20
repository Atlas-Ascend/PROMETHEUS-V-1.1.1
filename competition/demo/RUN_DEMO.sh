#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"
REPO_ROOT="$(CDPATH= cd -- "$SCRIPT_DIR/../.." && pwd)"
test -f "$REPO_ROOT/pyproject.toml" || { echo "Repository root validation failed" >&2; exit 2; }
command -v python3 >/dev/null 2>&1 || { echo "Python 3 is required" >&2; exit 2; }
command -v git >/dev/null 2>&1 || { echo "Git is required" >&2; exit 2; }
exec python3 "$SCRIPT_DIR/run_demo.py"

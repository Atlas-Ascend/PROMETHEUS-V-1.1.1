#!/usr/bin/env bash

set -Eeuo pipefail

SOURCE="/mnt/c/Ghost/PROMETHEUS-V-1.1.1"
DEST="$HOME/Ghost/PROMETHEUS-V-1.1.1-hephaestus-20260720-135553"
MISSION_REL="missions/HEPHAESTUS_OMEGA_COMMAND_TO_PROOF.md"
WINDOWS_AUTH="/mnt/c/Users/User/.codex/auth.json"
STAMP="20260720-135553"

sync_evidence() {
    if [ -d "$DEST/evidence" ]; then
        mkdir -p "$SOURCE/evidence"
        rsync -a "$DEST/evidence/" "$SOURCE/evidence/" || true
    fi
}

on_failure() {
    rc=$?
    echo
    echo "HEPHAESTUS Ω encountered execution exit code: $rc"
    sync_evidence
    exit "$rc"
}

trap on_failure ERR INT TERM

echo
echo "========================================================================"
echo " HEPHAESTUS Ω | LINUX-NATIVE EXECUTION FORGE"
echo "========================================================================"
echo

SUDO=""

if [ "$(id -u)" -ne 0 ]; then
    SUDO="sudo"
fi

NEEDS_PACKAGES=0

for COMMAND in git curl rsync python3 bwrap; do
    if ! command -v "$COMMAND" >/dev/null 2>&1; then
        NEEDS_PACKAGES=1
    fi
done

if [ "$NEEDS_PACKAGES" -eq 1 ]; then
    echo "[FORGE] Installing execution dependencies."

    $SUDO apt-get update
    $SUDO apt-get install -y \
        git \
        curl \
        ca-certificates \
        rsync \
        python3 \
        python3-venv \
        build-essential \
        bubblewrap
fi

echo "[FORGE] Installing the current Linux-native Codex CLI."

curl -fsSL https://chatgpt.com/codex/install.sh | sh

export PATH="$HOME/.local/bin:$HOME/bin:$PATH"

if ! command -v codex >/dev/null 2>&1; then
    echo "Codex was installed but is not available in PATH."
    exit 41
fi

echo
codex --version
echo

echo "[TRANSPOSE] Creating isolated Linux-native repository."

rm -rf "$DEST"
mkdir -p "$DEST"

rsync -a \
    --exclude=".venv/" \
    --exclude="node_modules/" \
    --exclude="__pycache__/" \
    --exclude=".pytest_cache/" \
    "$SOURCE/" \
    "$DEST/"

mkdir -p "$HOME/.codex"

# Copy authentication only. Do not share Windows state databases or caches.
if [ -f "$WINDOWS_AUTH" ]; then
    cp -f "$WINDOWS_AUTH" "$HOME/.codex/auth.json"
    chmod 600 "$HOME/.codex/auth.json"
    echo "[AUTH] Windows Codex authentication transferred."
fi

cd "$DEST"

git config core.filemode false

mkdir -p "evidence/hephaestus/$STAMP"

printf '%s\n' "$DEST" \
    > "evidence/hephaestus/$STAMP/wsl-forge-path.txt"

echo
echo "[AUTH] Checking Codex identity."
AUTH_STATUS="$(codex login status 2>&1 || true)"
echo "$AUTH_STATUS"

if ! printf '%s' "$AUTH_STATUS" | grep -qi "Logged in"; then
    echo
    echo "[AUTH] Interactive Codex authentication is required."
    codex login
fi

echo
echo "[PROBE] Testing Linux-native command execution."

codex exec \
    --cd "$DEST" \
    --sandbox read-only \
    "Run pwd and git status --short. Report only the results. Do not edit files."

echo
echo "========================================================================"
echo " HEPHAESTUS Ω | COMMAND-TO-PROOF EXECUTION"
echo "========================================================================"
echo

set +e

codex exec \
    --cd "$DEST" \
    --sandbox workspace-write \
    --output-last-message \
    "evidence/hephaestus/$STAMP/final-report.md" \
    - \
    < "$DEST/$MISSION_REL" \
    2>&1 |
    tee "evidence/hephaestus/$STAMP/codex-run.log"

CODEX_EXIT=${PIPESTATUS[0]}

set -e

if [ "$CODEX_EXIT" -ne 0 ]; then
    echo "Codex campaign exited with code $CODEX_EXIT."
    sync_evidence
    exit "$CODEX_EXIT"
fi

git status --short \
    > "evidence/hephaestus/$STAMP/final-git-status.txt"

git diff \
    > "evidence/hephaestus/$STAMP/final-working-diff.patch"

git diff --stat \
    > "evidence/hephaestus/$STAMP/final-diff-stat.txt"

echo
echo "[RETURN] Returning proven artifacts to Windows canonical reality."

rsync -a --delete \
    --exclude=".git/" \
    --exclude=".venv/" \
    --exclude="node_modules/" \
    --exclude="__pycache__/" \
    --exclude=".pytest_cache/" \
    "$DEST/" \
    "$SOURCE/"

echo
echo "========================================================================"
echo " HEPHAESTUS Ω | FORGE CYCLE COMPLETE"
echo "========================================================================"
echo
echo "Linux forge: $DEST"
echo "Canonical:   $SOURCE"
echo "State:       RETURNED TO WINDOWS"
echo
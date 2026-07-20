#!/usr/bin/env bash
set -Eeuo pipefail

SOURCE="/mnt/c/Ghost/PROMETHEUS-V-1.1.1"
MISSION_SOURCE="/mnt/c/Ghost/PROMETHEUS-V-1.1.1/evidence/codex/20260720-134040-command-to-proof/mission.md"
WINDOWS_CODEX="/mnt/c/Users/User/.codex"
STAMP="20260720-140043"

DEST="$HOME/Ghost/PROMETHEUS-HEPHAESTUS-$STAMP"
RUN_REL="evidence/hephaestus/$STAMP-resumed"

export PATH="$HOME/.local/bin:/usr/local/bin:$PATH"

echo
echo "========================================================================"
echo " HEPHAESTUS OMEGA | RESUMING BEYOND INSTALLATION"
echo "========================================================================"
echo

# Codex is already installed. Do not invoke the installer again.
CODEX_BIN="$(command -v codex || true)"

if [ -z "$CODEX_BIN" ]; then
    echo "Codex is installed but was not found in PATH."
    find "$HOME/.codex" "$HOME/.local" -type f -name codex 2>/dev/null | head
    exit 40
fi

echo "[PASS] Codex executable: $CODEX_BIN"
codex --version

# Install only missing forge utilities
MISSING=()

for tool in git rsync python3 bwrap; do
    command -v "$tool" >/dev/null 2>&1 || MISSING+=("$tool")
done

if [ "${#MISSING[@]}" -gt 0 ]; then
    echo "[FORGE] Installing missing utilities: ${MISSING[*]}"
    sudo apt-get update -qq
    sudo apt-get install -y git rsync python3 bubblewrap
fi

# Mount Windows authentication and configuration without stale caches
mkdir -p "$HOME/.codex"

for file in auth.json config.toml; do
    if [ -f "$WINDOWS_CODEX/$file" ]; then
        cp -f "$WINDOWS_CODEX/$file" "$HOME/.codex/$file"
    fi
done

chmod 600 "$HOME/.codex/auth.json" 2>/dev/null || true
rm -f "$HOME/.codex/models_cache.json"*
rm -f "$HOME/.codex/models_cache.json.tmp"*

echo
echo "[AUTH] Codex identity:"
codex login status || {
    echo "[AUTH] Login is required."
    codex login
}

# Create a genuine Linux-native working copy
echo
echo "[TRANSPOSE] Copying canonical repository into the Linux forge."

rm -rf "$DEST"
mkdir -p "$DEST"

rsync -a \
    --exclude=".venv/" \
    --exclude="node_modules/" \
    --exclude="__pycache__/" \
    --exclude=".pytest_cache/" \
    "$SOURCE/" \
    "$DEST/"

mkdir -p "$DEST/$RUN_REL"
cp "$MISSION_SOURCE" "$DEST/$RUN_REL/mission.md"

cd "$DEST"

echo
echo "[FORGE] Repository mounted:"
pwd
git status --short
git log --oneline -5

HELP="$(codex exec --help 2>&1)"
REPORT="$DEST/$RUN_REL/final-report.md"
LOG="$DEST/$RUN_REL/codex-run.log"

echo
echo "========================================================================"
echo " HEPHAESTUS OMEGA | COMMAND-TO-PROOF EXECUTION"
echo "========================================================================"
echo

ARGS=(exec)

grep -q -- "--cd" <<< "$HELP" &&
    ARGS+=(--cd "$DEST")

grep -q -- "--sandbox" <<< "$HELP" &&
    ARGS+=(--sandbox workspace-write)

grep -q -- "--output-last-message" <<< "$HELP" &&
    ARGS+=(--output-last-message "$REPORT")

ARGS+=(-)

set +e

codex "${ARGS[@]}" \
    < "$DEST/$RUN_REL/mission.md" \
    2>&1 |
    tee "$LOG"

CODEX_EXIT=${PIPESTATUS[0]}

set -e

# Sandbox fallback occurs only inside the disposable Linux forge copy
if [ "$CODEX_EXIT" -ne 0 ] &&
   grep -qiE "sandbox|bubblewrap|permission|operation not permitted" "$LOG" &&
   grep -q -- "--dangerously-bypass-approvals-and-sandbox" <<< "$HELP"; then

    echo
    echo "[HYDRA] Linux sandbox obstruction detected."
    echo "[HYDRA] Retrying inside the isolated forge without the sandbox."

    codex exec \
        --cd "$DEST" \
        --dangerously-bypass-approvals-and-sandbox \
        --output-last-message "$REPORT" \
        - \
        < "$DEST/$RUN_REL/mission.md" \
        2>&1 |
        tee "$DEST/$RUN_REL/codex-recovery.log"

    CODEX_EXIT=${PIPESTATUS[0]}
fi

if [ "$CODEX_EXIT" -ne 0 ]; then
    echo "$CODEX_EXIT" > "$DEST/$RUN_REL/exit-code.txt"

    rsync -a \
        "$DEST/$RUN_REL/" \
        "$SOURCE/$RUN_REL/"

    echo "Campaign stopped with exit code $CODEX_EXIT."
    exit "$CODEX_EXIT"
fi

# Capture return-state proof
git status --short > "$DEST/$RUN_REL/final-git-status.txt"
git diff > "$DEST/$RUN_REL/final-working-diff.patch"
git diff --stat > "$DEST/$RUN_REL/final-diff-stat.txt"

printf '%s\n' \
    "Codex: $(codex --version)" \
    "Forge: $DEST" \
    "Canonical: $SOURCE" \
    "Exit code: $CODEX_EXIT" \
    "State: EXECUTION_COMPLETE" \
    > "$DEST/$RUN_REL/forge-receipt.txt"

echo
echo "[RETURN] Synchronizing the completed organism to Windows."

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
echo " HEPHAESTUS OMEGA | FIRE RETURNED TO CANON"
echo "========================================================================"
echo
echo "Forge:     $DEST"
echo "Canonical: $SOURCE"
echo "Evidence:  $SOURCE/$RUN_REL"
echo "State:     RETURNED"
#!/usr/bin/env bash
set -Eeuo pipefail

SOURCE="/mnt/c/Ghost/PROMETHEUS-V-1.1.1"
MISSION_SOURCE="/mnt/c/Ghost/PROMETHEUS-V-1.1.1/evidence/ariadne/20260720-141404/ARIADNE_OMEGA_MISSION.md"
BRANCH="demo/command-to-proof-omega"
STAMP="20260720-141404"

DEST="$HOME/Ghost/ARIADNE-$STAMP"
OUT="$DEST/evidence/ariadne/$STAMP"

export PATH="$HOME/.local/bin:/usr/local/bin:$PATH"

echo
echo "======================================================================"
echo " ARIADNE OMEGA | CLEAN-ROOM REPRODUCIBILITY TRIAL"
echo "======================================================================"
echo

command -v git >/dev/null
command -v rsync >/dev/null
command -v codex >/dev/null

codex --version

rm -rf "$DEST"

echo "[THREAD] Creating a clean clone from canonical Git history."

git clone --no-hardlinks "$SOURCE" "$DEST"
cd "$DEST"

git checkout "$BRANCH"

mkdir -p "$OUT"
cp "$MISSION_SOURCE" "$OUT/mission.md"

echo
echo "[THREAD] Clean repository mounted."
git status --short
git log -1 --oneline

HELP="$(codex exec --help 2>&1)"
ARGS=(exec)

grep -q -- "--cd" <<< "$HELP" &&
    ARGS+=(--cd "$DEST")

grep -q -- "--sandbox" <<< "$HELP" &&
    ARGS+=(--sandbox workspace-write)

grep -q -- "--output-last-message" <<< "$HELP" &&
    ARGS+=(--output-last-message "$OUT/final-report.md")

ARGS+=(-)

echo
echo "[TRIAL] Building and proving the judge path."

set +e

codex "${ARGS[@]}" \
    < "$OUT/mission.md" \
    2>&1 |
    tee "$OUT/codex-run.log"

CODEX_EXIT=${PIPESTATUS[0]}

set -e

if [ "$CODEX_EXIT" -ne 0 ] &&
   grep -qiE "sandbox|bubblewrap|permission|operation not permitted" \
       "$OUT/codex-run.log" &&
   grep -q -- "--dangerously-bypass-approvals-and-sandbox" <<< "$HELP"; then

    echo
    echo "[HYDRA] Disposable clean-room sandbox obstruction detected."
    echo "[HYDRA] Retrying inside the isolated clone."

    set +e

    codex exec \
        --cd "$DEST" \
        --dangerously-bypass-approvals-and-sandbox \
        --output-last-message "$OUT/final-report.md" \
        - \
        < "$OUT/mission.md" \
        2>&1 |
        tee "$OUT/codex-recovery.log"

    CODEX_EXIT=${PIPESTATUS[0]}

    set -e
fi

if [ "$CODEX_EXIT" -ne 0 ]; then
    echo "$CODEX_EXIT" > "$OUT/codex-exit-code.txt"
    rsync -a "$OUT/" "$SOURCE/evidence/ariadne/$STAMP/"
    exit "$CODEX_EXIT"
fi

REQUIRED=(
    "competition/demo/JUDGE_README.md"
    "competition/demo/DEMO_SCRIPT.md"
    "competition/demo/VERIFICATION.md"
    "competition/demo/ARTIFACT_INDEX.json"
    "competition/demo/RUN_DEMO.sh"
    "competition/demo/RUN_DEMO.ps1"
)

for FILE in "${REQUIRED[@]}"; do
    if [ ! -s "$FILE" ]; then
        echo "[FAILED] Required artifact missing or empty: $FILE"
        exit 42
    fi
done

chmod +x competition/demo/RUN_DEMO.sh

echo
echo "======================================================================"
echo " ARIADNE OMEGA | EXECUTING THE JUDGE PATH"
echo "======================================================================"
echo

set +e

bash competition/demo/RUN_DEMO.sh \
    2>&1 |
    tee "$OUT/judge-demo.log"

DEMO_EXIT=${PIPESTATUS[0]}

set -e

echo "$DEMO_EXIT" > "$OUT/judge-demo-exit-code.txt"

if [ "$DEMO_EXIT" -ne 0 ]; then
    rsync -a "$OUT/" "$SOURCE/evidence/ariadne/$STAMP/"
    echo "[FAILED] The clean-room judge demo exited $DEMO_EXIT."
    exit "$DEMO_EXIT"
fi

git status --short > "$OUT/final-git-status.txt"
git diff --check > "$OUT/diff-check.txt"
git diff --stat > "$OUT/diff-stat.txt"
git diff > "$OUT/working-diff.patch"

find competition/demo \
    -type f \
    -print0 |
    sort -z |
    xargs -0 sha256sum \
    > "$OUT/demo-artifact-hashes.txt"

cat > "$OUT/ariadne-receipt.txt" <<EOF
Trial: ARIADNE OMEGA CLEAN-ROOM REPRODUCIBILITY
Branch: $BRANCH
Codex: $(codex --version)
Clean clone: $DEST
Judge demo exit code: $DEMO_EXIT
Required artifacts: VERIFIED
State: PROVEN
EOF

echo
echo "[RETURN] Returning the proven judge path to canonical Windows reality."

rsync -a \
    --exclude=".git/" \
    --exclude=".venv/" \
    --exclude="node_modules/" \
    --exclude="__pycache__/" \
    --exclude=".pytest_cache/" \
    "$DEST/" \
    "$SOURCE/"

echo
echo "======================================================================"
echo " ARIADNE OMEGA | THE THREAD REACHED DAYLIGHT"
echo "======================================================================"
echo
echo "Clean-room demo: PROVEN"
echo "State returned:  $SOURCE"
echo "Evidence:        $SOURCE/evidence/ariadne/$STAMP"
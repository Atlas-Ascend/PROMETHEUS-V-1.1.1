# Seven-Minute Judge Script

## 0:00 — Launch

Run `./competition/demo/RUN_DEMO.sh`. Point out repository-root discovery plus Python and Git validation. The process stops immediately and returns nonzero if a gate fails.

## 0:30 — Mission and candidates

Open the generated `campaign/<run-id>/mission.json` and `packets/`. The frozen mission is `P0-BOOTSTRAP-001`. Show the candidate result entries in `promotion-receipt.json`: each strategy has a distinct commit and isolated Git worktree.

## 1:30 — Measured execution and arbitration

Open `evidence/*/standard-initial/execution.json` and `evidence/arbitration.json`. These contain exact commands, working directories, timestamps, durations, exit codes, stdout/stderr paths, and hashes. The provisional leader is selected by the deterministic measured score.

## 2:30 — Adversarial reversal

Open the leader's `challenge-initial/execution.json`. The provisional leader fails the bool/NaN contract attack with a nonzero exit. This failure remains in the ledger and receipt.

## 3:30 — Repair and retest

Show the leader's repair commit in `promotion-receipt.json`, followed by `standard-retest/execution.json` and `challenge-retest/execution.json`. Both must exit 0 before promotion.

## 4:30 — Receipt and tamper rejection

Show the `proofgrid-receipt`, `evidence-tamper-rejected`, and `receipt-tamper-rejected` lines in `judge-transcript.log`. The probes operate on disposable copies; the original `promotion-receipt.json` remains valid.

## 5:30 — Genome and Build Truth

Open `capability-genome.json` and `build-truth.json`. Both link to the exact promotion receipt hash. Build Truth says `PROVEN` while explicitly retaining `discord_live_deployment: NOT_CLAIMED`.

## 6:30 — Close

Show `OMEGA_RESULT.json`, the generated `ARTIFACT_INDEX.json`, exit code 0, and the terminal result `PROMETHEUS OMEGA PROVEN`.

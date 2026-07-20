# PROMETHEUS OMEGA Judge Demonstration

Run one command from any directory inside the clone:

```bash
./competition/demo/RUN_DEMO.sh
```

On Windows PowerShell:

```powershell
& .\competition\demo\RUN_DEMO.ps1
```

The launchers discover the repository relative to their own location. They require Python 3.11+ and Git; the project has no third-party runtime dependencies. A successful run ends with the exact line `PROMETHEUS OMEGA PROVEN` and exit code 0. Any failed gate exits nonzero.

Each invocation creates a fresh, ignored directory at `competition/demo/evidence/OMEGA-<timestamp>-<id>/`. It never reads a prior evidence directory. `OMEGA_RESULT.json` is the gate verdict, `ARTIFACT_INDEX.json` contains exact SHA-256 hashes and sizes, and `judge-transcript.log` points each claim to generated evidence.

The demonstration executes the real `missions/bootstrap.json` P0 golden mission through `prometheus_kernel.engine.execute_mission`. It does not contact Discord, require credentials, depend on a Windows sandbox, or claim the P1 live deployment.

## Expected proof

The run creates three distinct candidate strategies in isolated Git worktrees, executes their standard tests, chooses the lowest-operation passing leader, records the leader's failed adversarial challenge, applies a repair commit, reruns standard and adversarial suites, promotes the repaired result, verifies the ProofGrid receipt, and validates its linked capability genome and Build Truth.

Two disposable copies prove rejection behavior: one mutates captured execution evidence and one mutates the promotion receipt. The canonical generated campaign remains untouched and verifiable.

## Truth boundary

`PROMETHEUS OMEGA PROVEN` means every local P0 gate listed in `OMEGA_RESULT.json` passed during that invocation. It does not mean a live Discord deployment occurred. No secret or credential is read or written by this package.

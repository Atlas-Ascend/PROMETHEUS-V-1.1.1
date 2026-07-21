# PROMETHEUS V-1.1.1

PROMETHEUS is a candidate-to-proof software engineering runtime. It accepts a mission, creates materially different implementations in isolated Git worktrees, runs local tests, challenges the leading result, repairs failures, promotes exactly one candidate, and emits a hash-verifiable promotion receipt plus capability genome.

## Active baseline

P0 is an executable ignition kernel—not the final platform. It proves this loop:

`mission → candidates → isolated execution → tests → adversarial challenge → repair → promotion → receipt → capability genome`

ServerForge is live and verified under HYDRA campaign `HYDRA-SERVERFORGE-20260719T023826Z`. P1 Recursive Forge now adds the missing Codex-backed self-build path: three concurrent Codex worktrees, passing-only arbitration, independent Codex challenge/repair, portable proof commitment, exact-confirmation Git push, draft PR creation, release packaging, and simultaneous ServerForge lifecycle publication.

## Requirements

- Python 3.11+
- Git 2.28+
- Codex CLI for recursive campaigns
- GitHub CLI for automatic draft-PR creation

No runtime Python dependencies are required.

## Install

```powershell
./scripts/Install-Prometheus.ps1
```

This creates a repository-local virtual environment, installs PROMETHEUS, runs the tests, and writes `PROMETHEUS.ps1` as the local launcher.

## Run the P0 proof

### Full ignition + ServerForge startup (PowerShell)

```powershell
./scripts/Start-Prometheus.ps1 -DryRun
```

For live ServerForge execution, create a new empty Discord server, install the Discord application into that exact server, set `DISCORD_APPLICATION_ID`, `DISCORD_GUILD_ID`, and `DISCORD_BOT_TOKEN` locally, then run:

```powershell
./scripts/Start-Prometheus.ps1 -ConfirmGuild $env:DISCORD_GUILD_ID
```

ServerForge captures a before-state backup before mutation and requires the confirmation value to exactly match the environment’s guild ID.

### Kernel only (PowerShell)

```powershell
./scripts/Invoke-Prometheus.ps1
```

### Any shell

```bash
python -m pip install -e .
python -m unittest discover -s tests -v
prometheus run missions/bootstrap.json
```

The run creates ignored evidence under `.prometheus/runs/<run-id>/`:

- three isolated candidate Git worktrees
- command results for standard and adversarial tests
- repaired and promoted workspace
- `promotion-receipt.json`
- `capability-genome.json`
- `summary.json`

Verify a receipt:

```bash
prometheus verify .prometheus/runs/<run-id>/promotion-receipt.json
```

## Run the full recursive campaign

The full command uses the authenticated local Codex and GitHub CLIs, preserves the verified ServerForge topology, publishes bounded live case-study events while candidates run, promotes only the passing leader, opens a draft PR, verifies the recursive receipt, and builds the wheel:

```powershell
./scripts/Run-PrometheusFullCampaign.ps1 `
    -ConfirmRepo 'Atlas-Ascend/PROMETHEUS-V-1.1.1' `
    -ConfirmGuild $env:DISCORD_GUILD_ID
```

Run real Codex candidates without GitHub or Discord mutation:

```powershell
./PROMETHEUS.ps1 recursive missions/self-build.json
```

Recursive proof is committed with the promoted lineage under `proof/recursive/<run-id>/`; local full transcripts and runtime evidence remain under `.prometheus/recursive/<run-id>/`.

## Repository map

- `src/prometheus_kernel/` — executable runtime
- `missions/` — declarative mission definitions
- `examples/bootstrap_target/` — deliberately incomplete P0 proving target
- `tests/` — kernel tests
- `docs/` — build truth, architecture, requirements, office, and case-study plan
- `scripts/` — operator entrypoints
- `serverforge/` — promoted Discord topology
- `schemas/` — machine-readable mission, topology, and receipt contracts
- `proof/recursive/` — portable committed self-build proof bundles

## Truth boundary

The current runtime performs real local Git operations, deterministic and Codex-backed candidate generation, parallel worktree execution, test arbitration, independent Codex challenge/repair, receipt verification, confirmed Git promotion, Discord planning and authenticated mutation, live topology verification, bounded case-study publication, Windows installation, and wheel packaging.

The repository tests use a fake Codex provider and do not prove a live model execution. A real recursive claim requires the authenticated local campaign and its verified receipt. Git worktrees are repository isolation, not OS-level sandboxing. Receipts are hash-bound but are not yet asymmetrically signed or externally timestamped.

See `docs/FULL_CAMPAIGN.md`, `docs/P1_RECURSIVE_FORGE_BUILD_TRUTH.md`, and `docs/INSTALLATION.md` for the complete design-to-proof path.

# PROMETHEUS V-1.1.1

PROMETHEUS is a candidate-to-proof software engineering runtime. It accepts a mission, creates materially different implementations in isolated Git worktrees, runs local tests, challenges the leading result, repairs failures, promotes exactly one candidate, and emits a hash-verifiable promotion receipt plus capability genome.

## Active baseline

P0 is an executable ignition kernel—not the final platform. It proves this loop:

`mission → candidates → isolated execution → tests → adversarial challenge → repair → promotion → receipt → capability genome`

ServerForge is bridged from startup. With Discord credentials present, the same operator command runs P0, captures the authorized server, applies the promoted topology, and verifies the live case-study surface. Without credentials it produces a complete zero-mutation plan.

## Requirements

- Python 3.11+
- Git 2.28+

No runtime Python dependencies are required.

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

## Repository map

- `src/prometheus_kernel/` — executable runtime
- `missions/` — declarative mission definitions
- `examples/bootstrap_target/` — deliberately incomplete P0 proving target
- `tests/` — kernel tests
- `docs/` — build truth, architecture, requirements, office, and case-study plan
- `scripts/` — operator entrypoints
- `serverforge/` — promoted Discord topology
- `schemas/` — machine-readable mission, topology, and receipt contracts

## Truth boundary

The current runtime performs real local Git operations, test execution, receipt verification, Discord planning, authenticated snapshot, role/channel/category application, and live topology verification. It does not yet generate arbitrary code with an LLM, provide OS-level sandbox isolation, sign receipts with an external identity, or claim a live Discord deployment until credentials are supplied and the live verification gate passes.

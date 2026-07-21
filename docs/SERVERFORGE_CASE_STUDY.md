# ServerForge Live Case Study Deployment

## Mission

Use the PROMETHEUS mission-to-proof kernel and the existing ServerForge bridge to populate, verify, and continuously update one Discord server explicitly authorized by its owner.

## Authorized target

- Guild ID: `1528216351636984036`
- Application ID: `1528218267540263065`
- Expected guild name: `PROMETHEUS Forge — Live Case Study`
- Target contract: `serverforge/case-study-target.json`
- Topology: `serverforge/topology.json`
- Baseline field report: `serverforge/publications/GAI-FR-20260721-PROM-SF-001.json`

The guild ID, application ID, and Discord public key are not credentials. The bot token is a credential and must remain only in Eden's local process environment or a managed secret store.

## One-time local secret setup

In the PowerShell session that launches PROMETHEUS:

```powershell
$SecureToken = Read-Host "Discord bot token" -AsSecureString
$env:DISCORD_BOT_TOKEN = [System.Net.NetworkCredential]::new("", $SecureToken).Password
```

Do not save the token in Git, `.env.example`, receipts, screenshots, console transcripts, or publication payloads.

## Dry-run proof

```powershell
./scripts/Start-Prometheus.ps1 -DryRun
```

This runs tests, executes and verifies the PROMETHEUS mission, plans the full ServerForge topology without mutation, validates the baseline publication payload, and validates the per-run case-study messages.

## Live deployment and console-run publication

```powershell
./scripts/Start-Prometheus.ps1 -ConfirmGuild 1528216351636984036
```

The live command performs the following governed sequence:

1. Run the kernel test suite.
2. Execute the mission-to-proof kernel.
3. Verify the generated promotion receipt.
4. Preflight the authorized Discord application and guild.
5. Capture a secrets-redacted before-state snapshot.
6. Reconcile the promoted ServerForge topology.
7. Verify topology and idempotency.
8. Publish the pinned Ghost Atlas Institute baseline case study.
9. Publish one idempotent proof episode for the console run across the case-study channels.
10. Write local Discord publication receipts without recording secret material.

## Channel population contract

### Public inspection surface

- `#welcome-to-the-forge`
- `#live-case-study`
- `#proof-index`
- `#promotion-receipts`
- `#capability-genomes`
- `#reproduction-lab`

### Private operating surface

- `#mission-intake`
- `#candidate-forge`
- `#promotion-gate`
- `#challenge-queue`
- `#findings`
- `#repair-verification`
- `#bridge-control`
- `#telemetry`
- `#incidents-and-rollback`

Every console run is marked with its unique PROMETHEUS run ID. Republishing the same run is idempotent and retains the existing messages instead of duplicating them.

## Case-study proof requirements

The live case study captures:

1. Authorized server identity and secrets-redacted before-state manifest.
2. Intended audience, workflows, roles, channels, permissions, onboarding, moderation, and observability.
3. Deterministic topology planning and idempotent reconciliation.
4. Adversarial permission, privilege-escalation, spam, recovery, and operator-usability evidence.
5. Repair records for material challenge findings.
6. Applied configuration and connected ServerForge runtime.
7. One real end-to-end console mission published through Discord.
8. Before/after evidence, health results, rollback proof, promotion receipt, and capability genome.

## Verification locations

- PROMETHEUS receipts: `.prometheus/runs/<run-id>/promotion-receipt.json`
- HYDRA ServerForge evidence: `.prometheus/serverforge/campaigns/<campaign-id>/`
- Baseline publication receipt: `artifacts/serverforge-publications/`
- Per-run Discord publication receipt: `artifacts/serverforge-console-runs/`

## Truth boundary

A repository patch does not prove that the Discord server was mutated. Live population is proven only after the local command runs with the authorized bot token and produces retrieval-verified Discord message receipts.

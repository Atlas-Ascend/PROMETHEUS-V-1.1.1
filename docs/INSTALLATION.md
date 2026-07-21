# Installation and Operation

## Requirements

- Windows 10/11 PowerShell
- Python 3.11 or newer
- Git 2.28 or newer
- Codex CLI installed and authenticated
- GitHub CLI authenticated when branch/PR publication is enabled
- Authorized Discord bot credentials when live ServerForge publication is enabled

## Install

```powershell
Set-Location 'C:\Ghost\PROMETHEUS-V-1.1.1'
& '.\scripts\Install-Prometheus.ps1'
```

The installer creates `.venv`, installs PROMETHEUS, runs tests, and creates the repository-local launcher `PROMETHEUS.ps1`.

## Deterministic P0 proof

```powershell
& '.\PROMETHEUS.ps1' run 'missions/bootstrap.json'
```

## Recursive P1 dry execution

This runs real Codex candidates but does not push, open a PR, or publish to Discord:

```powershell
& '.\PROMETHEUS.ps1' recursive 'missions/self-build.json'
```

## Full authenticated campaign

```powershell
& '.\scripts\Run-PrometheusFullCampaign.ps1' `
    -ConfirmRepo 'Atlas-Ascend/PROMETHEUS-V-1.1.1' `
    -ConfirmGuild $env:DISCORD_GUILD_ID
```

If `DISCORD_BOT_TOKEN` is absent, the runner requests it as a secure value. It is not written to the repository, proof bundle, Codex transcript, or release artifact.

## Build the release body

```powershell
& '.\scripts\Build-PrometheusRelease.ps1'
```

Artifacts are written under `dist/` with `release-manifest.json`.

## Verify a recursive receipt

```powershell
& '.\PROMETHEUS.ps1' verify-recursive `
    '<path-to-promotion-receipt.json>' `
    --workspace '<path-to-promoted-worktree>'
```

## Uninstall

PROMETHEUS is repository-local. Remove `.venv` and the generated `PROMETHEUS.ps1` launcher when no campaign is running. Evidence under `.prometheus` is intentionally separate from Git; preserve any receipts required for the case study before removing local runtime data.

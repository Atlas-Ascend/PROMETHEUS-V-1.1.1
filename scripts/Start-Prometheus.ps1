[CmdletBinding()]
param(
    [string]$Mission = "missions/bootstrap.json",
    [string]$Topology = "serverforge/topology.json",
    [string]$Target = "serverforge/case-study-target.json",
    [string]$Publication = "serverforge/publications/GAI-FR-20260721-PROM-SF-001.json",
    [switch]$DryRun,
    [switch]$NoCaseStudy,
    [string]$ConfirmGuild
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
Push-Location $Root

try {
    $env:PYTHONPATH = Join-Path $Root "src"

    $TargetPath = Join-Path $Root $Target
    if (-not (Test-Path -LiteralPath $TargetPath -PathType Leaf)) {
        throw "ServerForge case-study target not found: $TargetPath"
    }
    $TargetConfig = Get-Content -LiteralPath $TargetPath -Raw -Encoding UTF8 | ConvertFrom-Json

    if (-not $env:DISCORD_GUILD_ID) { $env:DISCORD_GUILD_ID = [string]$TargetConfig.guild_id }
    if (-not $env:DISCORD_APPLICATION_ID) { $env:DISCORD_APPLICATION_ID = [string]$TargetConfig.application_id }
    if (-not $env:DISCORD_PUBLIC_KEY) { $env:DISCORD_PUBLIC_KEY = [string]$TargetConfig.public_key }

    if ([string]$env:DISCORD_GUILD_ID -ne [string]$TargetConfig.guild_id) {
        throw "DISCORD_GUILD_ID does not match the authorized case-study target."
    }
    if (-not $ConfirmGuild) { $ConfirmGuild = [string]$TargetConfig.guild_id }
    if ([string]$ConfirmGuild -ne [string]$TargetConfig.guild_id) {
        throw "ConfirmGuild does not match the authorized case-study target."
    }

    Write-Host "" 
    Write-Host "============================================================" -ForegroundColor DarkCyan
    Write-Host " PROMETHEUS V-1.1.1 · COMMAND-TO-PROOF DEMO CONSOLE" -ForegroundColor Cyan
    Write-Host " Guild:       $($TargetConfig.guild_id)" -ForegroundColor White
    Write-Host " Application: $($TargetConfig.application_id)" -ForegroundColor White
    Write-Host " Mode:        $(if ($DryRun) { 'DRY RUN' } else { 'LIVE WHEN AUTHORIZED' })" -ForegroundColor White
    Write-Host "============================================================" -ForegroundColor DarkCyan

    python -m unittest discover -s tests -v
    if ($LASTEXITCODE -ne 0) { throw "PROMETHEUS kernel tests failed." }

    $Before = Get-Date
    python -m prometheus_kernel run $Mission
    if ($LASTEXITCODE -ne 0) { throw "PROMETHEUS ignition mission failed." }

    $Summary = Get-ChildItem (Join-Path $Root ".prometheus/runs") -Filter summary.json -File -Recurse -ErrorAction SilentlyContinue |
        Where-Object { $_.LastWriteTime -ge $Before.AddSeconds(-5) } |
        Sort-Object LastWriteTimeUtc -Descending |
        Select-Object -First 1
    if (-not $Summary) {
        $Summary = Get-ChildItem (Join-Path $Root ".prometheus/runs") -Filter summary.json -File -Recurse -ErrorAction SilentlyContinue |
            Sort-Object LastWriteTimeUtc -Descending |
            Select-Object -First 1
    }
    if (-not $Summary) { throw "PROMETHEUS completed without a discoverable summary.json." }

    $SummaryData = Get-Content -LiteralPath $Summary.FullName -Raw -Encoding UTF8 | ConvertFrom-Json
    python -m prometheus_kernel verify $SummaryData.receipt
    if ($LASTEXITCODE -ne 0) { throw "PROMETHEUS promotion receipt failed verification." }

    $HasLiveCredentials = [bool]$env:DISCORD_BOT_TOKEN
    if ($DryRun -or -not $HasLiveCredentials) {
        python -m prometheus_kernel serverforge plan $Topology
        if ($LASTEXITCODE -ne 0) { throw "ServerForge topology planning failed." }

        if (-not $NoCaseStudy) {
            & (Join-Path $PSScriptRoot "Publish-GhostAtlasCaseStudy.ps1") -Publication $Publication -ConfirmGuild $ConfirmGuild -DryRun
            & (Join-Path $PSScriptRoot "Publish-ConsoleRunCaseStudy.ps1") -SummaryPath $Summary.FullName -Target $Target -DryRun
        }

        if (-not $HasLiveCredentials -and -not $DryRun) {
            Write-Warning "DISCORD_BOT_TOKEN is absent. Local proof completed; ServerForge remained zero-mutation."
        }
        exit 0
    }

    python -m prometheus_kernel serverforge campaign $Topology --confirm-guild $ConfirmGuild
    if ($LASTEXITCODE -ne 0) { throw "HYDRA ServerForge topology campaign failed." }

    if (-not $NoCaseStudy) {
        & (Join-Path $PSScriptRoot "Publish-GhostAtlasCaseStudy.ps1") -Publication $Publication -ConfirmGuild $ConfirmGuild
        & (Join-Path $PSScriptRoot "Publish-ConsoleRunCaseStudy.ps1") -SummaryPath $Summary.FullName -Target $Target
    }

    Write-Host "" 
    Write-Host "============================================================" -ForegroundColor Green
    Write-Host " PROMETHEUS DEMO RUN · LOCAL PROOF + SERVERFORGE COMPLETE" -ForegroundColor Green
    Write-Host " Summary: $($Summary.FullName)" -ForegroundColor Cyan
    Write-Host " Guild:   $ConfirmGuild" -ForegroundColor Cyan
    Write-Host "============================================================" -ForegroundColor Green
}
finally {
    Pop-Location
}

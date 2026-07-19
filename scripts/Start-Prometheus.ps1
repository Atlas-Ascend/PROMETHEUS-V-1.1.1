[CmdletBinding()]
param(
    [string]$Mission = "missions/bootstrap.json",
    [string]$Topology = "serverforge/topology.json",
    [switch]$DryRun,
    [string]$ConfirmGuild
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
Push-Location $Root

try {
    $env:PYTHONPATH = Join-Path $Root "src"

    python -m unittest discover -s tests -v
    if ($LASTEXITCODE -ne 0) { throw "PROMETHEUS kernel tests failed." }

    python -m prometheus_kernel run $Mission
    if ($LASTEXITCODE -ne 0) { throw "PROMETHEUS ignition mission failed." }

    if ($DryRun -or -not $env:DISCORD_BOT_TOKEN -or -not $env:DISCORD_GUILD_ID) {
        python -m prometheus_kernel serverforge plan $Topology
        Write-Host "ServerForge live apply is waiting for DISCORD_BOT_TOKEN and DISCORD_GUILD_ID."
        exit 0
    }

    if (-not $ConfirmGuild) { $ConfirmGuild = $env:DISCORD_GUILD_ID }
    python -m prometheus_kernel serverforge campaign $Topology --confirm-guild $ConfirmGuild
    if ($LASTEXITCODE -ne 0) { throw "HYDRA ServerForge campaign failed." }
}
finally {
    Pop-Location
}

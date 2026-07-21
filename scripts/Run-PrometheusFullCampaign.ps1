[CmdletBinding()]
param(
    [string]$Root = (Split-Path -Parent $PSScriptRoot),
    [string]$Mission = 'missions/self-build.json',
    [Parameter(Mandatory = $true)]
    [string]$ConfirmRepo,
    [string]$ConfirmGuild = $env:DISCORD_GUILD_ID,
    [switch]$NoPush,
    [switch]$NoPullRequest,
    [switch]$NoServerForge
)

$ErrorActionPreference = 'Stop'
$Root = (Resolve-Path -LiteralPath $Root).Path
$Python = Join-Path $Root '.venv\Scripts\python.exe'
$TokenWasPresent = -not [string]::IsNullOrWhiteSpace($env:DISCORD_BOT_TOKEN)

Push-Location $Root
try {
    foreach ($Command in @('git', 'codex')) {
        if (-not (Get-Command $Command -ErrorAction SilentlyContinue)) {
            throw "Required command is unavailable: $Command"
        }
    }
    if (-not $NoPullRequest -and -not (Get-Command 'gh' -ErrorAction SilentlyContinue)) {
        throw "GitHub CLI 'gh' is required for draft-PR publication."
    }

    $Dirty = git status --porcelain
    if ($LASTEXITCODE -ne 0) {
        throw 'Git repository preflight failed.'
    }
    if ($Dirty) {
        throw 'The PROMETHEUS repository must be clean before recursive execution.'
    }

    git pull --ff-only
    if ($LASTEXITCODE -ne 0) {
        throw 'Git fast-forward synchronization failed.'
    }

    & (Join-Path $PSScriptRoot 'Install-Prometheus.ps1') -Root $Root

    codex login status
    if ($LASTEXITCODE -ne 0) {
        throw 'Codex is not authenticated. Run codex login, then restart the campaign.'
    }

    if (-not $NoServerForge) {
        if ([string]::IsNullOrWhiteSpace($ConfirmGuild)) {
            $ConfirmGuild = Read-Host 'Discord Guild ID'
        }
        $env:DISCORD_GUILD_ID = $ConfirmGuild
        if ([string]::IsNullOrWhiteSpace($env:DISCORD_BOT_TOKEN)) {
            $SecureToken = Read-Host 'Discord Bot Token' -AsSecureString
            $Pointer = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($SecureToken)
            try {
                $env:DISCORD_BOT_TOKEN = [Runtime.InteropServices.Marshal]::PtrToStringBSTR($Pointer)
            }
            finally {
                [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($Pointer)
            }
        }

        & $Python -m prometheus_kernel serverforge verify serverforge/topology.json
        if ($LASTEXITCODE -ne 0) {
            throw 'Existing ServerForge topology verification failed.'
        }
    }

    $Arguments = @(
        '-m', 'prometheus_kernel',
        'recursive', $Mission,
        '--confirm-repo', $ConfirmRepo
    )
    if (-not $NoPush) {
        $Arguments += '--push'
    }
    if (-not $NoPullRequest) {
        $Arguments += '--open-pr'
    }
    if (-not $NoServerForge) {
        $Arguments += '--publish-serverforge'
    }

    & $Python @Arguments
    if ($LASTEXITCODE -ne 0) {
        throw 'PROMETHEUS recursive campaign failed.'
    }

    $SummaryFile = Get-ChildItem '.prometheus\recursive' -Recurse -File -Filter 'summary.json' |
        Sort-Object LastWriteTime -Descending |
        Select-Object -First 1
    if (-not $SummaryFile) {
        throw 'Recursive campaign completed without a summary.'
    }
    $Summary = Get-Content -LiteralPath $SummaryFile.FullName -Raw | ConvertFrom-Json

    & $Python -m prometheus_kernel verify-recursive `
        $Summary.receipt `
        --workspace $Summary.promoted_workspace
    if ($LASTEXITCODE -ne 0) {
        throw 'Recursive promotion receipt verification failed.'
    }

    & (Join-Path $PSScriptRoot 'Build-PrometheusRelease.ps1') `
        -Root $Summary.promoted_workspace

    Write-Host ''
    Write-Host '==================================================' -ForegroundColor Green
    Write-Host ' PROMETHEUS V-1.1.1: FULL CAMPAIGN PROMOTED' -ForegroundColor Green
    Write-Host " Run:        $($Summary.run_id)" -ForegroundColor Cyan
    Write-Host " Leader:     $($Summary.leader)" -ForegroundColor Cyan
    Write-Host " Receipt:    $($Summary.receipt_hash)" -ForegroundColor Cyan
    Write-Host " Branch:     $($Summary.promotion_branch)" -ForegroundColor Cyan
    Write-Host " Draft PR:   $($Summary.draft_pr)" -ForegroundColor Cyan
    Write-Host " Discord:    $($Summary.serverforge_messages) messages" -ForegroundColor Cyan
    Write-Host '==================================================' -ForegroundColor Green
}
finally {
    if (-not $TokenWasPresent) {
        Remove-Item Env:\DISCORD_BOT_TOKEN -ErrorAction SilentlyContinue
    }
    Pop-Location
}

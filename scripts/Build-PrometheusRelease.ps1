[CmdletBinding()]
param(
    [string]$Root = (Split-Path -Parent $PSScriptRoot)
)

$ErrorActionPreference = 'Stop'
$Root = (Resolve-Path -LiteralPath $Root).Path
$Python = Join-Path $Root '.venv\Scripts\python.exe'
$Dist = Join-Path $Root 'dist'

if (-not (Test-Path -LiteralPath $Python)) {
    & (Join-Path $PSScriptRoot 'Install-Prometheus.ps1') -Root $Root
}

Push-Location $Root
try {
    New-Item -ItemType Directory -Path $Dist -Force | Out-Null
    & $Python -m pip wheel . --no-deps --wheel-dir $Dist
    if ($LASTEXITCODE -ne 0) {
        throw 'PROMETHEUS wheel build failed.'
    }

    $Artifacts = Get-ChildItem -LiteralPath $Dist -File |
        Sort-Object Name |
        ForEach-Object {
            [ordered]@{
                file = $_.Name
                bytes = $_.Length
                sha256 = (Get-FileHash -LiteralPath $_.FullName -Algorithm SHA256).Hash.ToLowerInvariant()
            }
        }

    $Manifest = [ordered]@{
        schema = 'prometheus.release-manifest.v1'
        version = '1.1.1'
        created_at = [DateTime]::UtcNow.ToString('o')
        artifacts = @($Artifacts)
    }
    $ManifestPath = Join-Path $Dist 'release-manifest.json'
    $Manifest | ConvertTo-Json -Depth 8 |
        Set-Content -LiteralPath $ManifestPath -Encoding UTF8

    Write-Host ''
    Write-Host 'PROMETHEUS RELEASE ARTIFACTS' -ForegroundColor Green
    $Artifacts | Format-Table -AutoSize
    Write-Host "Manifest: $ManifestPath" -ForegroundColor Cyan
}
finally {
    Pop-Location
}

[CmdletBinding()]
param(
    [string]$Mission = "missions/bootstrap.json",
    [switch]$SkipInstall
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
Push-Location $Root

try {
    if (-not $SkipInstall) {
        python -m pip install -e .
        if ($LASTEXITCODE -ne 0) { throw "Editable installation failed." }
    }

    python -m unittest discover -s tests -v
    if ($LASTEXITCODE -ne 0) { throw "Kernel tests failed." }

    python -m prometheus_kernel run $Mission
    if ($LASTEXITCODE -ne 0) { throw "PROMETHEUS mission failed." }
}
finally {
    Pop-Location
}

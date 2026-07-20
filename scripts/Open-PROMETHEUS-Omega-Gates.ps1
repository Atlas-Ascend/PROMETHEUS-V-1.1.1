#requires -Version 7.0

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$Repo = Split-Path -Parent $PSScriptRoot
$Engine = Join-Path $Repo "src\prometheus_omega\command_to_proof.py"

$PythonExe = $null
$PythonPrefix = @()

if (Get-Command py -ErrorAction SilentlyContinue) {
    & py -3.12 -c "import sys; assert sys.version_info >= (3, 12)" 2>$null

    if ($LASTEXITCODE -eq 0) {
        $PythonExe = "py"
        $PythonPrefix = @("-3.12")
    }
}

if (
    -not $PythonExe -and
    (Get-Command python -ErrorAction SilentlyContinue)
) {
    $PythonExe = "python"
}

if (-not $PythonExe) {
    throw "Python runtime not found."
}

Set-Location -LiteralPath $Repo

& $PythonExe @PythonPrefix $Engine run --repo $Repo

if ($LASTEXITCODE -ne 0) {
    throw "PROMETHEUS Command-to-Proof campaign failed."
}

& $PythonExe @PythonPrefix $Engine verify --repo $Repo

if ($LASTEXITCODE -ne 0) {
    throw "ProofGrid verification failed."
}
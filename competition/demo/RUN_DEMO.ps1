$ErrorActionPreference = "Stop"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$RepoRoot = (Resolve-Path (Join-Path $ScriptDir "../..")).Path
if (-not (Test-Path (Join-Path $RepoRoot "pyproject.toml") -PathType Leaf)) { throw "Repository root validation failed" }
$Python = Get-Command python -ErrorAction SilentlyContinue
if (-not $Python) { $Python = Get-Command py -ErrorAction SilentlyContinue }
if (-not $Python) { throw "Python 3.11 or newer is required" }
if (-not (Get-Command git -ErrorAction SilentlyContinue)) { throw "Git is required" }
& $Python.Source (Join-Path $ScriptDir "run_demo.py")
exit $LASTEXITCODE

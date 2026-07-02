param(
    [int]$Port = 5000
)

$ErrorActionPreference = "Stop"
$projectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $projectRoot

if (Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue) {
    Write-Error "Port $Port is already in use. Run '.\run-library.ps1 -Port 5001' or stop the other application."
}

$env:PORT = $Port

if (Test-Path ".\.venv\Scripts\python.exe") {
    & ".\.venv\Scripts\python.exe" "app.py"
} elseif (Get-Command python -ErrorAction SilentlyContinue) {
    & python "app.py"
} elseif (Get-Command py -ErrorAction SilentlyContinue) {
    & py "app.py"
} else {
    Write-Error "Python was not found. Install Python 3.12 or create a .venv environment."
}

$ErrorActionPreference = "Stop"
$venv = Join-Path $PSScriptRoot ".venv"
$python = Join-Path $venv "Scripts/python.exe"

if (-not (Test-Path -LiteralPath $python)) {
    py -3.13 -m venv $venv
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
}

& $python -m pip install -r (Join-Path $PSScriptRoot "requirements.txt")
exit $LASTEXITCODE

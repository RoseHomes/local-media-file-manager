$ErrorActionPreference = "Stop"

Push-Location (Join-Path $PSScriptRoot "..")
try {
    npm.cmd run build:css
    exit $LASTEXITCODE
} finally {
    Pop-Location
}

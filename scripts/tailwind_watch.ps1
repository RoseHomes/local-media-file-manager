$ErrorActionPreference = "Stop"

Push-Location (Join-Path $PSScriptRoot "..")
try {
    npm.cmd run watch:css
    exit $LASTEXITCODE
} finally {
    Pop-Location
}

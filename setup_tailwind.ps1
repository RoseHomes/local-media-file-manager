$ErrorActionPreference = "Stop"

Push-Location $PSScriptRoot
try {
    npm.cmd ci
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
    npm.cmd run build:css
    exit $LASTEXITCODE
} finally {
    Pop-Location
}

$ErrorActionPreference = 'Stop'
$repoRoot = Split-Path -Parent $PSScriptRoot

Push-Location (Join-Path $repoRoot 'apps/backend')
try {
    uv run python (Join-Path $repoRoot 'scripts/export_openapi.py')
}
finally {
    Pop-Location
}
$ErrorActionPreference = 'Stop'
$repoRoot = Split-Path -Parent $PSScriptRoot

Push-Location (Join-Path $repoRoot 'apps/backend')
try {
    uv python install 3.12
    uv sync --all-groups
}
finally {
    Pop-Location
}

Push-Location $repoRoot
try {
    corepack pnpm install --frozen-lockfile=false
}
finally {
    Pop-Location
}

Write-Host 'TaxMind Pro dependencies installed.'
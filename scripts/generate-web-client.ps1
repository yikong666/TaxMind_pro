$ErrorActionPreference = 'Stop'
$repoRoot = Split-Path -Parent $PSScriptRoot
$openapi = Join-Path $repoRoot 'packages/contracts/openapi/taxmind-v1.openapi.json'

if (-not (Test-Path -LiteralPath $openapi)) {
    throw "OpenAPI contract is missing: $openapi"
}

Push-Location $repoRoot
try {
    corepack pnpm --filter @taxmind/web generate:types
    corepack pnpm --filter @taxmind/web typecheck
}
finally {
    Pop-Location
}
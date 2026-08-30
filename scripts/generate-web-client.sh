#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
openapi="${repo_root}/packages/contracts/openapi/taxmind-v1.openapi.json"

if [[ ! -f "${openapi}" ]]; then
  echo "OpenAPI contract is missing: ${openapi}" >&2
  exit 1
fi

cd "${repo_root}"
corepack pnpm --filter @taxmind/web generate:types
corepack pnpm --filter @taxmind/web typecheck
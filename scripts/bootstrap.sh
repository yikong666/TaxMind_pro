#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

cd "${repo_root}/apps/backend"
uv python install 3.12
uv sync --all-groups

cd "${repo_root}"
corepack pnpm install --frozen-lockfile=false
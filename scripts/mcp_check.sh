#!/usr/bin/env bash
# Wrapper so OSS visitors can run this from the repo root.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
exec "$ROOT/backend/scripts/mcp_check.sh" "$@"

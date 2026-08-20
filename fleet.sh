#!/usr/bin/env bash
# Run the fleet CLI from anywhere.
#
#   ./fleet.sh status | tracks | lint | feedback | build --run --from mesh
#
# `python3 -m fleet.cli` only works from the repo root, and a build launched from a project
# directory dies instantly with ModuleNotFoundError — which looks exactly like every track failing
# at once. That misread cost three sweeps overnight. Use this instead.
set -euo pipefail
cd "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
exec python3 -u -m fleet.cli "$@"

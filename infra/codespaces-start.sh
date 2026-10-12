#!/usr/bin/env bash
set -euo pipefail
zen_root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$zen_root"
if [[ ! -f .env ]]; then
    echo "Run bash infra/codespaces-setup.sh once before starting."
    exit 1
fi
docker compose --env-file .env -f infra/compose.yml up -d --build --wait
echo "ZEN paper API and worker started. Open the Codespaces Ports panel for port 8080."
echo "This is a temporary development environment, not continuous live trading hosting."


#!/usr/bin/env bash
set -euo pipefail
zen_root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$zen_root"
python - <<'PY'
import base64, os, secrets
from pathlib import Path
path = Path(".env")
if not path.exists():
    data = {
        "POSTGRES_PASSWORD": secrets.token_urlsafe(32),
        "CREDENTIAL_MASTER_KEY": base64.b64encode(os.urandom(32)).decode(),
        "BOOTSTRAP_TOKEN": secrets.token_urlsafe(32),
        "MARKET_EXCHANGE": "bitget",
    }
    with path.open("x") as f:
        os.chmod(path, 0o600)
        f.write("".join(f"{k}={v}\n" for k, v in data.items()))
else:
    os.chmod(path, 0o600)
print("Private setup configuration ready; secrets were not printed.")
PY
bash infra/codespaces-start.sh


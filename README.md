# ZEN — private trading research workspace

Native Android application with a persistent Railway backend, real public crypto market data, a transactional paper trading ledger and independent risk controls.

**Release 0.4 adds redesigned Android screens, experimental LONG/SHORT paper futures and an owner-activated native MEXC manual execution path. Private exchange order acceptance is unvalidated; autonomous live strategies remain gated.** $200 is simulated starting equity. The $25 daily objective is aspirational and never an order quota.

## Install from your Android phone

1. Install the delivered ZEN Premium debug APK, or download the successful **Build Android APK** workflow artifact from GitHub Actions.
2. Open ZEN. The production backend address is already configured.
3. Select **Create account on the Welcome back card**, enter your own email and a password of at least 12 characters, then paste your private setup code from the owner setup note delivered separately.
4. Sign-in happens automatically after account creation. The code cannot create another owner once an account exists.
5. Paper mode allows automatic experimental LONG proposals from the backend scanner; you can also create your own paper order in Markets. The independent risk governor can veto either. Use Agent → Pause to block new entries.
6. Positions → Manage position supports protective exits, partial reductions and full close. Agent pause/resume controls new paper exposure. Emergency stop is in the header.
7. Exchange connections are optional for paper mode. Use only read-only keys with trading, transfers and withdrawals disabled. Private account access depends on exchange APIs, permissions and region.

Debug APKs are personal test builds. GitHub and local builds can have different debug signing keys; if Android rejects an update because the signatures differ, remove the previous test app before installing. Server-side account and history remain in PostgreSQL, but the local session is removed.

## Deployed backend

HTTPS API: `https://zen-api-production-8459.up.railway.app`

Railway has separate PostgreSQL, API and worker services in the selected Zain connection. The worker continues observing markets and monitoring paper exits when Android is closed. Application sleeping is disabled, subject to hosting account limits and outages. Hosting is metered; continuous execution is not guaranteed free.

The selected Railway account cannot access this repository directly. Deployment therefore uses the official public Python image with a **commit-pinned, SHA-256 verified source archive**. Hosting variables `SOURCE_COMMIT` and `SOURCE_SHA256` select the release. A mutable branch is never executed. Dependencies install at startup, so restart recovery can take longer than a prebuilt image; production container publishing is future deployment work. Database and credentials remain outside the container filesystem.

API health: `/health`. OpenAPI: `/openapi.json`. Authenticated APIs are protected by owner sessions. No real exchange order was sent during verification.

## Premium Android experience

Five native Compose tabs: Home, Markets, Agent, Positions, Settings. Restrained near-black surfaces, emerald/blue accents, legible decimal values, meaningful status states and guided forms. Features include real candle charts, order-book snapshots, watchlist, readable research decisions, risk editing, position reductions, confirmation dialogs, audit export and account sign-out.

Bearer sessions are encrypted with an Android Keystore AES-GCM key. Passwords and exchange secrets are not saved on the phone. Saved exchange credentials are encrypted server-side and never returned to the client.

## Research and execution boundary

The background worker now runs an autonomous experimental paper loop: observe → assess → propose → independent risk approval → simulated fill → TP/SL/time exits → fee-aware outcome audit. It scans BTC/ETH/SOL approximately every minute and monitors exits each worker pass. See [continuous paper release evidence](docs/AUTONOMOUS-PAPER.md). Spot LONG entries can execute automatically in Paper mode; separately selected paper futures supports LONG/SHORT experiments. See [0.4 implementation and certification boundaries](docs/RELEASE-0.4.md). The current research pipeline describes market structure and can conclude WAIT. No execution strategy has been promoted; descriptive signals and uncalibrated confidence are not treated as a trading edge. Automatic strategy training/promotion/rollback and full certified futures execution are unfinished. The tested historical baseline lost money after costs and was kept research-only.

Paper orders use fresh public bid/ask quotes, conservative modeled fees/slippage, account row locks and unique client IDs. Paper TP/SL runs on the worker; it is not an exchange-native protective order. Gaps or disconnections can exceed a planned loss. Private exchange keys and live sandbox orders have not been validated in this session.

## Validation and development

See [autonomous paper release evidence](docs/AUTONOMOUS-PAPER.md), [verified deployment](docs/AUTONOMOUS-DEPLOYMENT.json), and [earlier app end-to-end results](docs/DEPLOYMENT-E2E.json). Synthetic prices used for Android instrumentation exist only in the test APK; the production client has no demo balance or price feed.

```sh
pip install -r requirements.txt
python -m pytest -q
# PostgreSQL concurrency/migration checks are also run in GitHub CI.
python -m backend.manage init-dev
python -m backend.manage create-owner --email owner@example.com
python -m uvicorn backend.api:app --host 0.0.0.0 --port 8080
python -m backend.worker
```

Use PostgreSQL for deployment. Local SQLite is for isolated tests/development. Docker Compose setup is in `infra/compose.yml`; Codespaces testing is documented in [CODESPACES.md](docs/CODESPACES.md). Keep `.env`, setup codes, API keys and signing keystores out of source control.

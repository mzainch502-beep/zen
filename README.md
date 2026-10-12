# ZEN — Autonomous Crypto Trading Intelligence

Native Android client and persistent Python **paper spot trading foundation**. This is an engineering release, not the completed live futures product. No guaranteed returns. The $25/day objective is aspirational; $200 is explicitly simulated paper equity, not a deposited balance.

## Implemented

- FastAPI owner authentication, revocable sessions, optional one-time owner setup, encrypted read-only exchange credentials.
- PostgreSQL ledger with row-locked capital mutations and per-owner unique order IDs. SQLite only for local unit tests/development.
- Independent risk governor; paper fills, fees, marked portfolio, partial reductions, backend-monitored paper TP/SL, emergency stop of new exposure.
- Background market observer, Binance public book WebSocket, CCXT REST reads and reconnects; worker leadership lock.
- Research-only regime/trend pipeline returning WAIT until execution strategies are validated. No fabricated confidence.
- Cost-aware historical evaluation and chronological out-of-sample folds; promotion predicate. No automatic strategy mutation.
- Kotlin/Compose Android client: Home, Markets, Agent, Positions, Settings; real backend requests, candlestick view, owner setup, paper order testing, confirmation dialogs, risk controls, encrypted connection setup, audit export.
- GitHub Actions APK, backend CI/PostgreSQL concurrency test, dependency/secret scanning and optional Android UI test.

## Not implemented/certified

Live spot or futures execution, native private streams/TP-SL, shorting, leverage, hedge mode, cross margin, orderbook/trade/OI ingestion, LLM research service, automatic training/promotion/rollback, calibrated opportunity models, notifications and complete production hardening. Live activation always returns HTTP 409. Read-only key permission flags cannot be independently verified through every exchange; permission attestation is not certification.

The interface only shows controls supported by this release. See [validation report](docs/VALIDATION.md) and [architecture](docs/ARCHITECTURE.md) for evidence and gaps.

## Run backend

Python 3.12+, PostgreSQL 16+.

```sh
pip install -r requirements.txt
export DATABASE_URL='postgresql+psycopg://...'
python -m alembic -c database/alembic.ini upgrade head
python -m backend.manage create-owner --email owner@example.com
python -m uvicorn backend.api:app --host 0.0.0.0 --port 8080
# Separate terminal/container; continues when Android closes:
python -m backend.worker
```

For local isolated development: `python -m backend.manage init-dev` creates SQLite. Do not deploy SQLite across API/worker replicas.

Docker: copy `.env.example` to a private `.env`, configure secrets, run `docker compose --env-file .env -f infra/compose.yml up --build`. Host API behind TLS. The worker must start after migrations; if it races, restart worker. API docs are `/docs`, contract `/openapi.json`.

## Phone-only installation

1. Open this repository in GitHub on your phone, select **Actions → Build Android APK**.
2. Select **Run workflow → main**. Wait for a green run; failed builds do not produce a validated APK.
3. Open run → **Artifacts → ZEN-debug-APK**, download ZIP and extract `app-debug.apk`.
4. Install APK and permit installation from your download manager when Android requests it.
5. Enter your deployed **HTTPS API URL**, owner email and password. No API secret is embedded in the APK.
6. Use Settings to set paper risk limits. Agent Resume enables paper exposure; research currently stays WAIT. Use Markets paper test order to exercise the ledger.

A debug APK is for personal testing, not Play Store release. See [release signing](docs/ANDROID.md). Backend hosting is separate and must remain running; Android is a control surface, not the trading runtime.

## Railway

Provision a separate PostgreSQL, API and worker. API and worker use the same `DATABASE_URL` (SQLAlchemy `postgresql+psycopg` driver); only API receives `CREDENTIAL_MASTER_KEY`. API uses `infra/Dockerfile`, `/health`; worker uses the same image with `python -m backend.worker`, no HTTP healthcheck. Disable application sleeping, run one worker, and use private database networking. Public API must use Railway HTTPS domain. Railway free/trial limits can prevent service creation; continuous execution is not guaranteed free.

For phone-only first-owner setup, set a random 32+ character `BOOTSTRAP_TOKEN` in **API hosting variables**. In Android select Create owner account, enter that token and your own 12+ character password, then remove the hosting token after successful setup. Never put passwords or setup tokens into GitHub or public issue comments.

## Verify

```sh
python -m pytest -q
TEST_POSTGRES_URL='postgresql+psycopg://...' python -m pytest -q tests/test_postgres.py
python -m research.run probe --output docs/exchange-public-tests.json
python -m research.run history --exchange kraken --output docs/historical-evaluation.json
```

Public market probes do not validate private keys, regional eligibility or live execution. Test fixtures are synthetic and confined to tests; UI has no demo prices.

## GitHub-only temporary backend testing

A Codespaces configuration is included. From Android, select Code → Codespaces → Create codespace on main. PostgreSQL, API and paper worker start through Docker Compose. See [phone-only setup and limitations](docs/CODESPACES.md). This does not provide continuous production trading hosting.


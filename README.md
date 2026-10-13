# ZEN — institutional Android research desk

ZEN 0.6 is a native Android application with a persistent Railway backend, real public market feeds, separate spot/futures paper books, bounded contextual learning and an independent risk governor. The interface has been redesigned around a premium dark/light design system and an original adaptive ZEN icon.

[Download ZEN 0.6 APK](https://github.com/mzainch502-beep/zen/releases/download/zen-debug-38446791918/app-debug.apk) · [Verified release](docs/RELEASE-0.6-VERIFIED.md) · [Workflows and boundaries](docs/INSTITUTIONAL-0.6.md)

This is an experimental, owner-managed research platform. No profitable strategy or reliable daily income is established. Automatic live strategies remain gated. The latest historical replay lost after modeled costs and was not promoted.

## Install and operate entirely from Android

1. Download the APK above and allow installation from your browser/file manager. You can also open GitHub → Actions → Build Android APK → Run workflow, then download/extract the successful APK artifact.
2. Sign in to your existing owner account. The Railway backend address is preconfigured. For first-time setup only, choose Create account and use the private setup code previously delivered separately; this code cannot create a second owner. Never put it in GitHub.
3. Home → paper capital setup initializes a single simulated capital amount, explicitly split between spot and futures. Close existing simulated positions first. Review the amount, leverage ceiling, automatic risk recommendation switch and automatic-entry permission, then confirm.
4. Use the persistent **Automatic trading** ON/OFF switch for new entries. The agent can choose LONG, SHORT where derivatives permit it, or WAIT. It can remain in cash for an entire day. It never trades solely to reach an income target.
5. Portfolio → Manage position opens protective exits, partial reductions and close controls. AI exposes real decisions and learning history. Emergency trading halt is in the header; it stops new entries while protective management continues. Existing exposure requires explicit close/reduction.
6. More opens strategies, risk management, recorded performance, exchange connections, market context, audit export, appearance and account controls. Exchange keys are unnecessary for public data and paper trading. Direct stock-broker integration is deferred.

Debug builds can have different signing keys across GitHub runners. If Android rejects an update due to a signature mismatch, uninstall the earlier test app, install this APK and sign in again. Local sessions are removed; PostgreSQL account history remains. Owner-managed release signing is documented in [Android operations](docs/ANDROID.md). Never commit a keystore.

## Portfolio and research

Tabs: **Home | Portfolio | Trade | AI | More**. Inter and IBM Plex Mono fonts are bundled with their licenses. The original monogram is a vector adaptive launcher icon. Light mode has an explicit contrast palette; it is not an inverted dark theme. Every displayed valuation, chart point, market quote and decision comes from its backend source. Instrumentation fixtures exist only in the test APK.

The futures observer discovers the venue's supported USDT perpetual catalogue and scans rotating liquid/API-eligible candle batches. Spot alternatives use their own completed candles. Spot cannot open naked SHORT positions. Stock-linked/index-linked products are classified from venue metadata and labeled as derivatives, not shares; underlying sessions and corporate-action rules remain unverified. Discoverability does not certify product suitability, account permission or private order execution.

Shared paper capital is not duplicated between books. Both books obey their own governor plus aggregate exposure, entry-rate, position-count, daily-loss and drawdown limits. Automatic risk recommendations can tighten owner ceilings using paper evidence; they cannot expand live permissions or guarantee loss prevention. A 500× simulated ceiling is available for stress settings, but actual venue limits, costs, minimums and liquidation checks still apply. It does not force 500× positions or imply a safe $3 live account.

Learning records completed exposure outcomes after costs, aggregating partial closes, and adjusts strategy/regime preferences only within bounded paper gates. Improvement after every trade, calibrated confidence and human professional discretion are not established. Limited public RSS metadata supplies research context; failures are visible and headlines cannot place orders.

## Persistent backend

API: `https://zen-api-production-8459.up.railway.app` · health `/health` · contracts `/openapi.json`.

Railway runs PostgreSQL, API, market/research worker and execution worker separately. Trading state and protective paper management persist when the phone closes or signs out; turn automation OFF first if you want to prevent new entries. Hosting is metered and subject to account limits/outages. It cannot be replaced by a reliable phone-only background process.

Deployment uses the official Python 3.12 image and a commit-pinned, SHA-256-verified source archive. `SOURCE_COMMIT` and `SOURCE_SHA256` select the release; a mutable branch is never executed. Dependencies install on startup, so recovery is slower than a prebuilt container. Secrets and database storage remain outside container source.

Owner sessions are protected by Android Keystore encryption, TLS, server-side credential encryption, session revocation and account authorization. Exchange secrets are never returned to the app. Withdrawals are unsupported. MFA and password recovery are explicitly unavailable. No private exchange order was sent during this release's verification.

Native MEXC manual execution remains experimental behind explicit owner activation. Automatic live trading, universal private futures adapters, complete funding settlement, private protective-order certification, LLM provider configuration, iOS/web applications and public fund management remain unfinished. See the release report before using real funds.

## Development

```sh
pip install -r requirements.txt
python -m pytest -q
python -m backend.manage init-dev
python -m backend.manage create-owner --email owner@example.com
python -m uvicorn backend.api:app --host 0.0.0.0 --port 8080
python -m backend.worker
```

PostgreSQL concurrency and migration tests run in GitHub CI. SQLite is only for isolated tests/development. See [Docker Compose](infra/compose.yml), [Codespaces](docs/CODESPACES.md), [Security](docs/SECURITY.md) and [architecture](docs/ARCHITECTURE.md). Keep API keys, setup codes and `.env` out of source control.

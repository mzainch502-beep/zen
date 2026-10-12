# ZEN 0.2 release evidence

## What changed

Rebuilt the native client into separated design system, repository, controller and screen modules. Added a custom Z mark, a focused portfolio summary, readable research activity, interactive candlestick inspection, market depth, watchlist, guided owner setup, secure session persistence, position-management sheets, risk editing and a two-stage read-only exchange connection flow. Every exposed action targets the real backend or a device-local preference/export operation.

Backend additions: account/agent summaries, order-book endpoint, public setup availability, PostgreSQL bootstrap locking, paper-fill activity metadata and mark-based high-water tracking. An admin-only CLI can remove explicitly disposable deployment-test accounts; it refuses ordinary owner addresses and is not exposed over HTTP.

## Verified

- Native debug compilation and Android lint: successful.
- Android emulator: sign-in fields, authenticated loading, five-tab navigation, pause confirmation/API request and risk sheet passed. UI screenshots use synthetic instrumentation-only responses; they are design QA, not account/performance evidence.
- Backend unit/API tests passed locally; PostgreSQL concurrency, migrations, dependency audit and secret scanning run in GitHub CI.
- Railway PostgreSQL, API and worker reached SUCCESS. Public TLS `/health` reported status ok and worker_online true.
- Cloud end-to-end test passed 13 checks: first-owner setup, login, authorized snapshot, actual BTC/ETH/SOL quotes, mode changes, risk-approved paper buy, duplicate-order prevention, reduce-only close, fees, actual depth, historical candles, live activation lock and session revocation.
- No real exchange order, withdrawal or transfer was sent.
- The disposable verification account was removed. First-owner setup is available for the real owner.

## Exact boundaries

This is a deployed paper spot release, not a certified autonomous live futures system. Live order adapters, exchange-native exits/private streams, futures margin/liquidation/shorting, calibrated strategy selection, autonomous learning/promotion/rollback and full real-device performance/accessibility testing remain incomplete. Read-only credential handling is implemented, but no private exchange key was supplied for validation.

The API/worker use a reviewed source commit and source-archive checksum on Railway's public Python image because this Railway connection lacks repository access. Database/keys are persistent hosting resources. Dependencies install on restart; this has a recovery-time cost and is not a high-availability deployment claim.

Defaults: simulated equity $200, spot 1×, $2 modeled loss/trade, $6 daily loss, $40 exposure, two simultaneous positions. The $25 daily goal is aspirational. Opening new exposure can be vetoed; reductions remain possible after pause/stop if executable quotes are fresh.

# Validation evidence — 2026-10-12

## Scope

This is a tested backend paper-trading foundation and native Android implementation. It is **not a completed or certified live futures trading product**. No real-money trade was sent. Starting paper equity $200 is simulated and labelled accordingly.

## Results

- Backend unit/API tests: latest exact result in `test-results.xml`; 40 passed, 1 skipped after setup/rate/minimum checks. PostgreSQL concurrency test is skipped locally because PostgreSQL is not provisioned; CI supplies PostgreSQL.
- Actual public exchange probes (`exchange-public-tests.json`): OKX, Coinbase and Bitget returned real executable quotes. Binance, Bybit, Kraken, KuCoin, Gate and MEXC probes failed in this environment; they are not certified. Kraken historical candles were separately accessible even though ticker timestamp validation rejected its ticker. API construction tests for all nine adapters are not connectivity certification.
- Historical baseline (`historical-evaluation.json`): 719 completed Kraken BTC/USDT 5-minute candles, 128 trade-side changes, modeled net return −22.4096%, max drawdown 22.4096%, fees 10 bps and slippage 10 bps per side. Fixed chronological next-bar baseline; three subsequent out-of-sample folds retained in JSON. It stays research-only. Small historical sample and one market do not justify deployment.
- Credential tests: AES-GCM encryption/decryption and wrong owner/exchange authenticated context rejection. No real private API key provided; private account permissions and sandbox order placement untested.
- Order tests: PostgreSQL-style row lock design, duplicate idempotency response, fingerprint mismatch rejection, fee/P&L arithmetic, risk vetoes, stale/future data, invalid reduction, unknown/partial state tracker, bounded read retries.
- Android: Compose source and build workflow provided; local Gradle compilation/lint status will be recorded after build. Offline Compose smoke test is present; emulator/device tests not yet executed.
- Production: Railway project `zen-autonomous` created. Database service provisioning was rejected with `Free plan resource provision limit exceeded`. Template request queued but no service materialized. No functioning hosted backend is claimed.

## Unvalidated / absent

Live spot/futures orders, all futures account modes, leverage, contract sizing, native protective orders, private streams, signed command replay security, account permissions verification, sandbox execution, reconciliation after exchange partitions, distributed production auth throttling, model calibration/training/rollback, cloud recovery drills, complete Android real-device UX and performance. Owner live activation remains hard-blocked.

## Reproduction

`python -m pytest -q`; use CI for real PostgreSQL. `python -m research.run probe --output docs/exchange-public-tests.json`; `python -m research.run history --exchange kraken --output docs/historical-evaluation.json`. Exchange requests must be permitted by host network and exchange region. TLS verification stays enabled; corporate/proxy root CA is read only from explicit SSL_CERT_FILE.

# Historical release 0.1 report

This report is archived evidence. The deployed and redesigned release is described in [RELEASE-0.2.md](RELEASE-0.2.md).

# Validation evidence — 2026-10-12

## Scope

This is a tested backend paper-trading foundation and native Android implementation. It is **not a completed or certified live futures trading product**. No real-money trade was sent. Starting paper equity $200 is simulated and labelled accordingly.

## Results

- Backend unit/API tests: latest exact result in `test-results.xml`; 40 passed, 1 skipped after setup/rate/minimum checks. PostgreSQL concurrency test is skipped locally; GitHub CI supplied PostgreSQL and passed all 41 tests, including four simultaneous duplicate requests. Successful run: https://github.com/mzainch502-beep/zen/actions/runs/38201253327 .
- Actual public exchange probes (`exchange-public-tests.json`): Coinbase and Bitget returned real executable quotes on the security-compatible pinned CCXT version. OKX was accessible with the newer dependency-conflicted CCXT version but fails with the selected version. Binance, Bybit, OKX, Kraken, KuCoin, Gate and MEXC probes failed in this environment; they are not certified. Kraken historical candles were separately accessible even though ticker timestamp validation rejected its ticker. API construction tests for all nine adapters are not connectivity certification.
- Historical baseline (`historical-evaluation.json`): 719 completed Kraken BTC/USDT 5-minute candles, 128 trade-side changes, modeled net return −22.4096%, max drawdown 22.4096%, fees 10 bps and slippage 10 bps per side. Fixed chronological next-bar baseline; three subsequent out-of-sample folds retained in JSON. It stays research-only. Small historical sample and one market do not justify deployment.
- Credential tests: AES-GCM encryption/decryption and wrong owner/exchange authenticated context rejection. No real private API key provided; private account permissions and sandbox order placement untested.
- Order tests: PostgreSQL-style row lock design, duplicate idempotency response, fingerprint mismatch rejection, fee/P&L arithmetic, risk vetoes, stale/future data, invalid reduction, unknown/partial state tracker, bounded read retries.
- Android: Compose source and build workflow provided; local `:app:assembleDebug :app:lintDebug` completed BUILD SUCCESSFUL with exit 0; debug APK generated (approximately 9.7 MiB). Offline Compose smoke test is present; GitHub emulator offline-sign-in smoke test passed: https://github.com/mzainch502-beep/zen/actions/runs/38201468540 . Full backend-backed navigation and real-device UX remain unverified.
- Production: Railway project `zen-autonomous` created. Database service provisioning was rejected with `Free plan resource provision limit exceeded`. Template request queued but no service materialized. No functioning hosted backend is claimed.

## Unvalidated / absent

Live spot/futures orders, all futures account modes, leverage, contract sizing, native protective orders, private streams, signed command replay security, account permissions verification, sandbox execution, reconciliation after exchange partitions, distributed production auth throttling, model calibration/training/rollback, cloud recovery drills, complete Android real-device UX and performance. Owner live activation remains hard-blocked.

## Reproduction

`python -m pytest -q`; use CI for real PostgreSQL. `python -m research.run probe --output docs/exchange-public-tests.json`; `python -m research.run history --exchange kraken --output docs/historical-evaluation.json`. Exchange requests must be permitted by host network and exchange region. TLS verification stays enabled; corporate/proxy root CA is read only from explicit SSL_CERT_FILE.

Dependency scan: no known vulnerabilities after selecting CCXT 4.4.100 with multidict 6.9.1. CCXT 4.5.85 pins vulnerable multidict 6.7.1; it is not used. Exchange support is narrower on the selected version; latest probe results are authoritative.

Real-public-quote paper smoke test passed: simulated buy and close on a Bitget BTC/USDT quote, simulated final cash 199.9599991646, costs recorded, zero real exchange orders. See paper-smoke.json. GitHub secret scan: no leaks found; dependency audit: no known vulnerabilities.

Runtime smoke: separate API and market worker processes ran successfully with real Bitget BTC/ETH/SOL quotes persisted to a temporary database; health reported worker_online=true. This was local testing, not cloud deployment. See runtime-smoke.json.

APK build artifact: https://github.com/mzainch502-beep/zen/actions/runs/38201253264 . Android lint passed with two non-blocking warnings (application icon and data-extraction-rule declaration); no Android lint errors.

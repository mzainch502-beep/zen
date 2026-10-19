# ZEN 0.9.0 validation evidence — 19 October 2026

## Completed checks

- Android APK compile and lint: GitHub Actions run **39258569979**, success.
- Android emulator UI instrumentation: run **39258569982**, success.
- APK SHA-256: `5898a12b234e5ce8d200e0164c58b6621d38905454397074f5a4c569ee1e6aa8`.
- Backend, PostgreSQL migration, and security checks: run **39259313744**,
  **129 tests passed**, one warning; secret and dependency scanning passed.
- Fresh capital accounting and paper SHORT/idempotency/emergency-stop/authentication
  checks passed in workerd in run **39258569887**.

## Production issue found during verification

The first activated deployment exceeded Cloudflare's isolate memory limit during
background operation. It was not accepted as ready. The follow-up removes eager
loading of nine exchange classes and replaces the spot observer's full CCXT market
catalogue with symbol-specific public Bitget V3 reads. Added tests reject stale,
mismatched, crossed and non-finite spot quotes. Runtime tests now exercise fresh
activation plus the production alarm handler with a clearly identified fixture
observer; they do not submit real orders or claim profitable trades.

## Release scope

This release starts a new, owner-created **paper** workspace; no Railway data is
imported. The existing APK UI connects to the new Cloudflare URL. Paper automation
starts after owner setup, subject to fees, freshness, liquidity and risk vetoes.
The aggressive preset uses a 5x ceiling, not unrestricted exchange leverage.
A daily profit target is not an execution quota.

There is no evidence yet of a one-week paper performance record, profitability,
real-money exchange execution, uninterrupted free-tier operation, or readiness to
manage public funds. APK testing used the Android emulator, not the owner's phone.

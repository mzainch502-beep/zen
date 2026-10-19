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

## Production verification update — 19 October 2026, 18:18 UTC

The final deployed revision `64942138c7c6eac32a357c68baaf6aa3d4db5da5`
passed deployment run **39260913480**. Background heartbeats continue updating.
Production logs identify HTTP **403** responses for all three Bitget spot reads,
and the MEXC futures feed remains unavailable. At verification there were zero
provisioned owners, zero usable market catalogue entries, and no validated
production paper trades. Do not describe this deployment as trading-ready.

The installable Android artifact remains run **39258569979**. A functioning APK
and passing fixture tests do not resolve exchange access restrictions. An
exchange/provider-approved data connection is required; no proxy or regional
restriction bypass is implemented. Railway data has not been imported or deleted.

## Market-feed correction — 19 October 2026

The unavailable MEXC futures feed was traced to an internal JavaScript runtime
error: Cloudflare rejects fetch redirect mode `error`. Revision
`5a0e30480332e8fd56c725efbc1ec486f17d363b` uses `manual` and still rejects non-2xx
responses. The deployed durable heartbeat subsequently reported 649 contracts.
This supersedes the earlier inference that MEXC access itself was blocked.

Revision `f0b18f17b96ee2da8e6417e59784167884af8b27` replaces the Bitget spot observer
and Cloudflare spot charts/depth with a native MEXC public reader. Backend CI run
39303912923 passed 137 tests; deployment/runtime validation is separate. Spot
quote freshness uses the latest exchange trade timestamp; the REST book has no
exchange timestamp and depth exposes receipt time separately. Unsupported 3m
spot candles return an unavailable response instead of invented candles.

No owner was provisioned at verification. Market-data recovery does not establish
that production paper orders have occurred, that paper returns are profitable,
or that Binance/Bybit live execution is validated. No new APK is necessary for
these backend-only corrections; Android 0.9.0 already points to Cloudflare.

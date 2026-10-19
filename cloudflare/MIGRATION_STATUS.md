# Cloudflare fresh paper deployment

The owner requested a fresh workspace on 19 October 2026; Railway account data is
not imported or deleted. Android 0.9.0 (version code 12) uses
`https://zen-api.zen-fatishorizon.workers.dev`.

## New owner setup

Choose **Create account** in the APK, enter an email, a password of at least 12
characters, and the private one-use owner setup code. The code is a Cloudflare
secret, never part of the APK or repository. Setup closes after the first owner.
Remove `BOOTSTRAP_TOKEN` from Worker secrets after successful setup.

`ZEN_PAPER_PROFILE=aggressive` provisions exactly $200 simulated capital:
$50 spot and $150 futures. It enables combined automatic paper trading with a
5x maximum futures leverage, $3 margin per proposed position, up to three futures
positions, $2 maximum trade loss, $6 daily loss ceiling, and $20 drawdown ceiling.
Aggregate portfolio checks still apply. These are ceilings, not trade guarantees.
An existing account's cash, limits and history are never reset by a deployment.
Live autonomous execution remains unavailable on this runtime.

## Background work

Durable Object alarms refresh public quotes and manage paper exits independently
of Android. The next alarm is armed before each cycle (10 seconds); a one-minute
Cron invocation restores a missing alarm. Network reads run concurrently with
8-second timeouts, and the overall cycle has a 22-second timeout. Financial
transactions remain serialized. Long cycles can delay the next alarm.

A dynamic MEXC contract catalogue and bulk ticker feed cover supported perpetuals;
liquidity, spread, freshness and exchange API availability filter eligibility.
Four contracts receive candle research per minute, prioritizing held positions,
volatility and a rotating catalogue. The rotation cursor survives eviction. Spot
research uses BTC, ETH and SOL on alternating cycles. No fixed trade count or
profit quota forces an order. Exit and risk checks can leave the account in cash.

## Validation and limitations

The deployment workflow gates publishing on actual workerd tests for authentication,
exact financial decimals, database transactions/rollback, credential encryption,
fresh capital allocation, paper SHORT orders, duplicate prevention, emergency stop,
and session revocation. Test prices are explicitly fixtures, not performance data.
Android workflows compile, lint, and run navigation instrumentation tests.

Public exchange access and background execution must also be checked using deployed
Worker logs and durable heartbeat records. Passing fixture tests does not establish
profitable performance, live execution readiness, or continuous uptime.

Cloudflare free-tier CPU, request and database quotas can stop service. No paid plan
was enabled. Observe actual usage before treating this as production infrastructure.
Portfolio snapshots are spaced at five minutes to reduce writes. Runtime quote
caches are volatile and refresh after eviction; stale quotes cannot authorize entry.
Android uses authenticated HTTP polling; `/events` WebSocket is unavailable here.
The Railway privileged live executor and geopolitical context poller are not ported.
This is a paper-testing release, not a public fund-management launch.

## Deployment

Use the Cloudflare account for fatishorizon@gmail.com. GitHub secret
`CLOUDFLARE_API_TOKEN` authorizes the existing deployment workflow. Worker secrets
`CREDENTIAL_MASTER_KEY` and `BOOTSTRAP_TOKEN` are provisioned separately. Never rotate
the master key without reencrypting any stored credentials. Keep an owner-controlled
backup/recovery process before storing real exchange credentials.

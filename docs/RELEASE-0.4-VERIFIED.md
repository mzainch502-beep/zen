# ZEN 0.4 validation evidence

The redesigned Android APK compiled and passed lint; three Android UI tests passed. Eighty backend checks passed, including PostgreSQL concurrency, legacy-schema upgrade, native LONG/SHORT order construction, decimal precision, ambiguous-write reconciliation, revoked-connection checks and bounded leadership handover.

Railway API, market worker, privileged executor and PostgreSQL are verified online. Real MEXC public contract feeds report BTC and ETH ceilings of 500× and SOL 300×. These are public contract ceilings, not private-account leverage guarantees.

A temporary local paper ledger seeded with $3 opened and closed a simulated BTC SHORT using actual quotes from the cloud observer. It ended at 2.970373578168 USDT after modeled costs. It used no private exchange credentials, changed no production owner, and sent no exchange order. This is execution/accounting evidence, not evidence of profitability.

Manual native MEXC connection and live activation workflows are implemented, but private order acceptance is untested. Autonomous live strategy deployment remains gated. The $25 daily objective is aspirational. Full funding accounting, native protection-status reconciliation, hedge/cross modes and validated adaptive learning are unfinished.

See `RELEASE-0.4-DEPLOYMENT.json` and the referenced GitHub Actions runs for source commits and evidence. The final backend source is 46dd1d6495e9ceeda9f2ad86cfe7e3c0649f9b7d; the verified APK source is 019a2ffe577f68c2cdd41d5d25af6f0e69ca0f40.
